"""
Load Balancer — Intelligent API key rotation, health tracking, and failover.

Features:
  - Round-robin key selection with health-aware fallback
  - Per-key rate-limit tracking with exponential cooldown
  - Concurrent request throttling per key
  - Real-time health scoring based on success/error/429 rates
  - Transparent failover: if primary key is unhealthy, routes to best alternative
  - Dashboard stats for monitoring key health
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class KeyStats:
    """Tracks health and usage metrics for a single API key."""
    total_requests: int = 0
    successful: int = 0
    errors: int = 0
    rate_limits: int = 0
    consecutive_failures: int = 0
    last_rate_limit: float = 0.0
    last_error: float = 0.0
    last_success: float = 0.0
    cooldown_until: float = 0.0
    active_requests: int = 0
    total_response_time: float = 0.0

    @property
    def avg_response_time(self):
        if self.successful == 0:
            return 0.0
        return self.total_response_time / self.successful

    @property
    def success_rate(self):
        if self.total_requests == 0:
            return 1.0
        return self.successful / self.total_requests

    @property
    def health_score(self):
        """
        Composite health score (0.0 to 1.0).
        Factors: success rate, recency of errors, cooldown status, active load.
        """
        now = time.time()

        # Base: success rate (weight: 40%)
        sr = self.success_rate * 0.4

        # Recency penalty: recent errors/429s reduce score (weight: 30%)
        recency = 0.3
        if self.last_rate_limit > 0:
            secs_since_rl = now - self.last_rate_limit
            # Decays from 1.0 penalty to 0 over 120 seconds
            rl_penalty = max(0, 1.0 - (secs_since_rl / 120))
            recency -= rl_penalty * 0.2
        if self.last_error > 0:
            secs_since_err = now - self.last_error
            err_penalty = max(0, 1.0 - (secs_since_err / 60))
            recency -= err_penalty * 0.1
        recency = max(0, recency)

        # Consecutive failure penalty (weight: 20%)
        consec = max(0, 0.2 - (self.consecutive_failures * 0.05))

        # Load penalty: fewer active requests = better (weight: 10%)
        load = max(0, 0.1 - (self.active_requests * 0.02))

        return min(1.0, max(0.0, sr + recency + consec + load))


class LoadBalancer:
    """
    Manages a pool of API keys with intelligent routing.

    Usage:
        lb = LoadBalancer(keys=['key1', 'key2', 'key3'])
        key = lb.acquire_key(preferred_index=0)
        try:
            result = make_api_call(key)
            lb.report_success(key, response_time=1.5)
        except RateLimitError:
            lb.report_rate_limit(key)
        except Exception:
            lb.report_error(key)
        finally:
            lb.release_key(key)
    """

    def __init__(self, keys, max_concurrent_per_key=3, base_cooldown=5.0,
                 max_cooldown=120.0):
        self.keys = [k for k in keys if k]  # Filter out empty keys
        self.max_concurrent = max_concurrent_per_key
        self.base_cooldown = base_cooldown
        self.max_cooldown = max_cooldown

        self._lock = threading.Lock()
        self._stats: dict[str, KeyStats] = {k: KeyStats() for k in self.keys}
        self._round_robin_idx = 0

        # Semaphores for concurrent request limiting per key
        self._semaphores = {k: threading.Semaphore(max_concurrent_per_key)
                           for k in self.keys}

    def _is_available(self, key):
        """Check if a key is available (not in cooldown, not overloaded)."""
        stats = self._stats[key]
        now = time.time()

        # In cooldown?
        if now < stats.cooldown_until:
            return False

        # Too many active requests?
        if stats.active_requests >= self.max_concurrent:
            return False

        return True

    def _get_cooldown_duration(self, key):
        """Exponential backoff cooldown based on consecutive failures."""
        stats = self._stats[key]
        # 5s, 10s, 20s, 40s, 80s, 120s (capped)
        duration = self.base_cooldown * (2 ** min(stats.consecutive_failures, 5))
        return min(duration, self.max_cooldown)

    def acquire_key(self, preferred_index=None):
        """
        Get the best available API key.

        Args:
            preferred_index: Optional index hint (e.g., from model config).
                             Will be used if that key is healthy, otherwise
                             falls back to the best alternative.

        Returns:
            The selected API key string, or None if all keys are exhausted.
        """
        with self._lock:
            if not self.keys:
                return None

            # Try preferred key first if it's healthy
            if preferred_index is not None and 0 <= preferred_index < len(self.keys):
                preferred_key = self.keys[preferred_index]
                if self._is_available(preferred_key):
                    stats = self._stats[preferred_key]
                    if stats.health_score >= 0.3:
                        stats.active_requests += 1
                        stats.total_requests += 1
                        return preferred_key

            # Find the best available key by health score
            candidates = []
            for key in self.keys:
                if self._is_available(key):
                    candidates.append((key, self._stats[key].health_score))

            if candidates:
                # Sort by health score (descending), pick the best
                candidates.sort(key=lambda x: x[1], reverse=True)
                best_key = candidates[0][0]
                self._stats[best_key].active_requests += 1
                self._stats[best_key].total_requests += 1
                return best_key

            # All keys are in cooldown or overloaded — pick the one with
            # the shortest remaining cooldown
            now = time.time()
            soonest = None
            soonest_wait = float('inf')
            for key in self.keys:
                stats = self._stats[key]
                wait = max(0, stats.cooldown_until - now)
                if wait < soonest_wait:
                    soonest = key
                    soonest_wait = wait

            if soonest:
                self._stats[soonest].active_requests += 1
                self._stats[soonest].total_requests += 1
                return soonest

            # Absolute fallback: round-robin
            key = self.keys[self._round_robin_idx % len(self.keys)]
            self._round_robin_idx += 1
            self._stats[key].active_requests += 1
            self._stats[key].total_requests += 1
            return key

    def release_key(self, key):
        """Release a key back to the pool after a request completes."""
        if key not in self._stats:
            return
        with self._lock:
            self._stats[key].active_requests = max(
                0, self._stats[key].active_requests - 1
            )

    def report_success(self, key, response_time=0.0):
        """Report a successful API call."""
        if key not in self._stats:
            return
        with self._lock:
            stats = self._stats[key]
            stats.successful += 1
            stats.consecutive_failures = 0
            stats.last_success = time.time()
            stats.total_response_time += response_time

    def report_rate_limit(self, key):
        """Report a 429 rate-limit response. Applies exponential cooldown."""
        if key not in self._stats:
            return
        with self._lock:
            stats = self._stats[key]
            stats.rate_limits += 1
            stats.consecutive_failures += 1
            stats.last_rate_limit = time.time()
            cooldown = self._get_cooldown_duration(key)
            stats.cooldown_until = time.time() + cooldown
            print(f"  [LB] Key ...{key[-6:]} rate-limited → cooldown {cooldown:.0f}s "
                  f"(consecutive: {stats.consecutive_failures})")

    def report_error(self, key):
        """Report a non-rate-limit error."""
        if key not in self._stats:
            return
        with self._lock:
            stats = self._stats[key]
            stats.errors += 1
            stats.consecutive_failures += 1
            stats.last_error = time.time()
            # Shorter cooldown for generic errors
            cooldown = min(self.base_cooldown * stats.consecutive_failures,
                           self.max_cooldown / 2)
            stats.cooldown_until = time.time() + cooldown

    def get_dashboard(self):
        """Return health dashboard data for all keys."""
        with self._lock:
            dashboard = []
            for i, key in enumerate(self.keys):
                stats = self._stats[key]
                now = time.time()
                dashboard.append({
                    'index': i,
                    'key_suffix': f"...{key[-6:]}",
                    'health_score': round(stats.health_score, 3),
                    'success_rate': round(stats.success_rate, 3),
                    'total_requests': stats.total_requests,
                    'successful': stats.successful,
                    'errors': stats.errors,
                    'rate_limits': stats.rate_limits,
                    'active_requests': stats.active_requests,
                    'avg_response_time': round(stats.avg_response_time, 2),
                    'in_cooldown': now < stats.cooldown_until,
                    'cooldown_remaining': round(
                        max(0, stats.cooldown_until - now), 1
                    ),
                    'consecutive_failures': stats.consecutive_failures,
                })
            return dashboard

    def get_best_key_index(self):
        """Return the index of the currently healthiest key."""
        with self._lock:
            best_idx = 0
            best_score = -1
            for i, key in enumerate(self.keys):
                score = self._stats[key].health_score
                if score > best_score:
                    best_score = score
                    best_idx = i
            return best_idx
