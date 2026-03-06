"""
LLM engine for the fight arena.

Supports mixed-model benchmarking with provider-aware routing, latency timing,
and resilient Gemini API key failover.
"""

import json
import os
import re
import time

import requests
from dotenv import load_dotenv

try:
    from .load_balancer import LoadBalancer
except ImportError:
    from load_balancer import LoadBalancer

load_dotenv()


def _first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _clamp(value, lower, upper):
    return max(lower, min(upper, value))


def _to_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


DEFAULT_MODEL_SLOTS = {
    "1": {
        "name": "Gemini 2.5 Flash",
        "model_id": "gemini-2.5-flash",
        "provider": "gemini",
        "api_key_index": 0,
        "description": "Fast and agile. Built to win the latency race.",
        "color": "#4285f4",
    },
    "2": {
        "name": "Gemini 2.5 Pro",
        "model_id": "gemini-2.5-pro",
        "provider": "gemini",
        "api_key_index": 1,
        "description": "Heavyweight strategist. Slower reads, stronger plans.",
        "color": "#ea4335",
    },
    "3": {
        "name": "Gemini 2.0 Flash",
        "model_id": "gemini-2.0-flash",
        "provider": "gemini",
        "api_key_index": 0,
        "description": "Previous-gen speedster with a stable jab.",
        "color": "#7c3aed",
    },
    "4": {
        "name": "Flash-Lite Preview",
        "model_id": "gemini-2.5-flash-preview-04-17",
        "provider": "gemini",
        "api_key_index": 1,
        "description": "Experimental build. Cheap, twitchy, and volatile.",
        "color": "#f59e0b",
    },
}

GEMINI_API_KEYS = [
    os.getenv("GEMINI_API_KEY_1", "").strip(),
    os.getenv("GEMINI_API_KEY_2", "").strip(),
]

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_TIMEOUT = _to_int(os.getenv("OLLAMA_TIMEOUT"), 60)

lb = LoadBalancer(
    keys=GEMINI_API_KEYS,
    max_concurrent_per_key=3,
    base_cooldown=5.0,
    max_cooldown=120.0,
)


def _build_model_registry():
    models = {}
    for slot_id, defaults in DEFAULT_MODEL_SLOTS.items():
        provider = _first_non_empty(
            os.getenv(f"FIGHTER_{slot_id}_PROVIDER"),
            defaults["provider"],
        ).lower()

        if provider == "ollama":
            model_id = _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_MODEL_ID"),
                os.getenv(f"OLLAMA_MODEL_{slot_id}"),
                os.getenv("OLLAMA_DEFAULT_MODEL"),
                "llama3.2",
            )
        else:
            model_id = _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_MODEL_ID"),
                defaults["model_id"],
            )

        models[slot_id] = {
            "fighter_id": slot_id,
            "skin_id": slot_id,
            "name": _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_NAME"),
                defaults["name"],
            ),
            "model_id": model_id,
            "provider": provider,
            "api_key_index": _to_int(
                os.getenv(f"FIGHTER_{slot_id}_API_KEY_INDEX"),
                defaults.get("api_key_index", 0),
            ),
            "description": _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_DESCRIPTION"),
                defaults["description"],
            ),
            "color": _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_COLOR"),
                defaults["color"],
            ),
        }
    return models


MODELS = _build_model_registry()

BASE_PARAMS = {
    "temperature": 0.7,
    "top_p": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "max_tokens": 500,
}

FIGHT_SYSTEM = (
    "You are an LLM boxer in a live benchmark arena. "
    "Return only valid JSON with these keys: "
    '"thinking" (short strategic summary, 2-3 sentences max), '
    '"move" (exactly one of PUNCH, KICK, DEFEND, DUCK, MOVE_FORWARD, MOVE_BACKWARD), '
    '"confidence" (number between 0 and 1), '
    '"prediction" (short guess about the opponent\'s next move).'
)


def get_lb_dashboard():
    """Return health details for Gemini key routing."""
    if not lb.keys:
        return []
    return lb.get_dashboard()


def _masked_key(api_key):
    if not api_key:
        return "unconfigured"
    return f"...{api_key[-6:]}"


def _base_result(elapsed=0.0, text="", error=None, error_type=None, key_used="n/a"):
    return {
        "text": text,
        "error": error,
        "error_type": error_type,
        "response_time": elapsed,
        "key_used": key_used,
    }


def call_gemini(model_id, prompt, params, api_key):
    """Call Gemini with a single API key attempt."""
    if not api_key:
        return _base_result(error="Gemini API key is missing", error_type="config", key_used="missing")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:generateContent?key={api_key}"
    )

    generation_config = {
        "temperature": _clamp(_to_float(params.get("temperature"), 0.7), 0.0, 2.0),
        "topP": _clamp(_to_float(params.get("top_p"), 1.0), 0.1, 1.0),
        "maxOutputTokens": max(80, _to_int(params.get("max_tokens"), 500)),
    }

    presence_penalty = _to_float(params.get("presence_penalty"), 0.0)
    frequency_penalty = _to_float(params.get("frequency_penalty"), 0.0)
    if presence_penalty != 0.0:
        generation_config["presencePenalty"] = _clamp(presence_penalty, -2.0, 2.0)
    if frequency_penalty != 0.0:
        generation_config["frequencyPenalty"] = _clamp(frequency_penalty, -2.0, 2.0)

    payload = {
        "system_instruction": {"parts": [{"text": FIGHT_SYSTEM}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }

    started = time.time()
    try:
        response = requests.post(url, json=payload, timeout=45)
    except Exception as exc:
        elapsed = time.time() - started
        return _base_result(
            elapsed=elapsed,
            error=str(exc),
            error_type="network",
            key_used=_masked_key(api_key),
        )

    elapsed = time.time() - started
    key_used = _masked_key(api_key)

    if response.status_code == 429:
        return _base_result(
            elapsed=elapsed,
            error="429: rate limited",
            error_type="rate_limit",
            key_used=key_used,
        )

    if response.status_code != 200:
        return _base_result(
            elapsed=elapsed,
            error=f"{response.status_code}: {response.text[:400]}",
            error_type="api",
            key_used=key_used,
        )

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        reason = data.get("promptFeedback", {}).get("blockReason", "no candidate returned")
        return _base_result(
            elapsed=elapsed,
            error=f"Blocked: {reason}",
            error_type="blocked",
            key_used=key_used,
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        finish_reason = candidates[0].get("finishReason", "unknown")
        return _base_result(
            elapsed=elapsed,
            error=f"Empty response (finish={finish_reason})",
            error_type="empty",
            key_used=key_used,
        )

    return _base_result(
        elapsed=elapsed,
        text=parts[0].get("text", ""),
        key_used=key_used,
    )


def call_ollama(model_id, prompt, params):
    """Call Ollama's HTTP API for local or remote models."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    headers = {}
    if OLLAMA_API_KEY:
        headers["Authorization"] = f"Bearer {OLLAMA_API_KEY}"

    repeat_penalty = 1.0
    repeat_penalty += _clamp(_to_float(params.get("frequency_penalty"), 0.0), 0.0, 2.0) * 0.35
    repeat_penalty += _clamp(_to_float(params.get("presence_penalty"), 0.0), 0.0, 2.0) * 0.2

    payload = {
        "model": model_id,
        "prompt": f"{FIGHT_SYSTEM}\n\n{prompt}",
        "stream": False,
        "options": {
            "temperature": _clamp(_to_float(params.get("temperature"), 0.7), 0.0, 2.0),
            "top_p": _clamp(_to_float(params.get("top_p"), 1.0), 0.1, 1.0),
            "num_predict": max(80, _to_int(params.get("max_tokens"), 500)),
            "repeat_penalty": _clamp(repeat_penalty, 1.0, 2.0),
        },
    }

    started = time.time()
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=OLLAMA_TIMEOUT)
    except Exception as exc:
        elapsed = time.time() - started
        return _base_result(
            elapsed=elapsed,
            error=str(exc),
            error_type="network",
            key_used="ollama",
        )

    elapsed = time.time() - started
    if response.status_code != 200:
        return _base_result(
            elapsed=elapsed,
            error=f"{response.status_code}: {response.text[:400]}",
            error_type="api",
            key_used="ollama",
        )

    data = response.json()
    return _base_result(
        elapsed=elapsed,
        text=data.get("response", ""),
        key_used="ollama-cloud" if OLLAMA_API_KEY else "ollama-local",
    )


def _call_gemini_with_failover(info, prompt, params):
    if not lb.keys:
        return _base_result(error="No Gemini API keys configured", error_type="config", key_used="missing")

    attempts = max(1, min(len(lb.keys), 4))
    last_result = None

    for attempt in range(attempts):
        preferred_index = info.get("api_key_index", 0) if attempt == 0 else None
        api_key = lb.acquire_key(preferred_index=preferred_index)
        if not api_key:
            break

        try:
            result = call_gemini(info["model_id"], prompt, params, api_key)
            last_result = result

            if result["error_type"] == "rate_limit":
                lb.report_rate_limit(api_key)
                continue

            if result["error_type"]:
                lb.report_error(api_key)
            else:
                lb.report_success(api_key, result["response_time"])
            return result
        finally:
            lb.release_key(api_key)

    if last_result:
        return last_result

    return _base_result(error="All Gemini keys are unavailable", error_type="config", key_used="missing")


def call_model(fighter_id, prompt, sabotage_params):
    """Route a fighter request to its configured provider."""
    info = MODELS.get(str(fighter_id))
    if not info:
        return _base_result(error=f"Unknown fighter: {fighter_id}", error_type="config", key_used="n/a")

    params = {**BASE_PARAMS, **(sabotage_params or {})}
    provider = info.get("provider", "gemini").lower()

    if provider == "gemini":
        return _call_gemini_with_failover(info, prompt, params)

    if provider == "ollama":
        return call_ollama(info["model_id"], prompt, params)

    return _base_result(
        error=f"Unsupported provider: {provider}",
        error_type="config",
        key_used="n/a",
    )


MOVE_ALIASES = {
    "BOX": "PUNCH",
    "MOVE FORWARD": "MOVE_FORWARD",
    "MOVE BACKWARD": "MOVE_BACKWARD",
    "MOVE BACK": "MOVE_BACKWARD",
    "FORWARD": "MOVE_FORWARD",
    "BACKWARD": "MOVE_BACKWARD",
}


def _extract_thinking(data):
    return (
        str(data.get("thinking", "")).strip()
        or str(data.get("reasoning", "")).strip()
        or str(data.get("analysis", "")).strip()
        or "No reasoning."
    )[:500]


def _normalize_move(move):
    raw = str(move or "DEFEND").upper().strip().replace("-", "_")
    raw = raw.replace("  ", " ")
    raw = MOVE_ALIASES.get(raw, raw)
    return raw.replace(" ", "_")


def parse_llm_response(text):
    """Parse a model response into a normalized fight move payload."""
    valid_moves = ["PUNCH", "KICK", "DEFEND", "DUCK", "MOVE_FORWARD", "MOVE_BACKWARD"]

    if not text or not text.strip():
        return _default("No response from model")

    clean = text.strip()
    clean = re.sub(r"<think>.*?</think>", "", clean, flags=re.DOTALL).strip()
    clean = re.sub(r"```(?:json)?\s*", "", clean).strip()

    start = clean.find("{")
    if start == -1:
        return _fallback(clean, valid_moves, text)

    json_blob = clean[start:]

    try:
        data = json.loads(json_blob)
        return _from_data(data, valid_moves, text)
    except json.JSONDecodeError:
        pass

    for suffix in ['"}', '"}', "}"]:
        try:
            data = json.loads(json_blob + suffix)
            return _from_data(data, valid_moves, text)
        except json.JSONDecodeError:
            continue

    move_match = re.search(r'"(?:move|action)"\s*:\s*"([^"]+)"', json_blob)
    think_match = re.search(r'"(?:thinking|reasoning|analysis)"\s*:\s*"([^"]*)', json_blob)
    confidence_match = re.search(r'"confidence"\s*:\s*([\d.]+)', json_blob)
    prediction_match = re.search(r'"prediction"\s*:\s*"([^"]*)', json_blob)

    if move_match:
        move = _normalize_move(move_match.group(1))
        if move in valid_moves:
            return {
                "thinking": think_match.group(1) if think_match else "Extracted from partial response",
                "move": move,
                "confidence": float(confidence_match.group(1)) if confidence_match else 0.5,
                "prediction": prediction_match.group(1) if prediction_match else "Unknown",
                "raw": text,
            }

    return _fallback(clean, valid_moves, text)


def _from_data(data, valid_moves, raw):
    move = _normalize_move(data.get("move", data.get("action", "DEFEND")))
    if move not in valid_moves:
        move = "DEFEND"
    return {
        "thinking": _extract_thinking(data),
        "move": move,
        "confidence": _clamp(_to_float(data.get("confidence"), 0.5), 0.0, 1.0),
        "prediction": str(data.get("prediction", "Unknown"))[:200],
        "raw": raw,
    }


def _fallback(clean, valid_moves, raw):
    upper = clean.upper()
    for move in ["MOVE_FORWARD", "MOVE_BACKWARD", "KICK", "PUNCH", "DUCK", "DEFEND", "BOX"]:
        if move in upper:
            normalized = _normalize_move(move)
            if normalized in valid_moves:
                return {
                    "thinking": clean[:300],
                    "move": normalized,
                    "confidence": 0.3,
                    "prediction": "Unknown",
                    "raw": raw,
                }
    return _default(clean[:300])


def _default(message):
    return {
        "thinking": message,
        "move": "DEFEND",
        "confidence": 0.1,
        "prediction": "Unknown",
        "raw": "",
    }
