"""
LLM engine for the fight arena.

Supports mixed-model benchmarking with provider-aware routing across Ollama
and Groq.
"""

import json
import os
import re
import time

import requests
from dotenv import load_dotenv

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
        "name": "Qwen 3.5",
        "model_id": "qwen3.5:latest",
        "provider": "ollama",
        "skin_id": "1",
        "description": "Ollama Cloud multimodal generalist with strong overall utility.",
        "color": "#ffffff",
    },
    "2": {
        "name": "Groq Llama 3.3 70B",
        "model_id": "llama-3.3-70b-versatile",
        "provider": "groq",
        "skin_id": "2",
        "description": "Groq production model optimized for quality with solid reasoning range.",
        "color": "#f55036",
    },
    "3": {
        "name": "GPT OSS 20B",
        "model_id": "openai/gpt-oss-20b",
        "provider": "groq",
        "skin_id": "3",
        "description": "OpenAI open-weight 20B model hosted on Groq.",
        "color": "#6ef2ff",
    },
    "4": {
        "name": "Groq Llama 3.1 8B",
        "model_id": "llama-3.1-8b-instant",
        "provider": "groq",
        "skin_id": "4",
        "description": "Fast Groq production model tuned for low latency.",
        "color": "#ffb347",
    },
}

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_TIMEOUT = _to_int(os.getenv("OLLAMA_TIMEOUT"), 60)
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_TIMEOUT = _to_int(os.getenv("GROQ_TIMEOUT"), 45)
GROQ_RETRY_ATTEMPTS = max(1, _to_int(os.getenv("GROQ_RETRY_ATTEMPTS"), 2))
GROQ_RETRY_BASE_DELAY = _to_float(os.getenv("GROQ_RETRY_BASE_DELAY"), 1.25)
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "llama-3.1-8b-instant").strip()


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
                defaults["model_id"],
            )
        elif provider == "groq":
            model_id = _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_MODEL_ID"),
                os.getenv(f"GROQ_MODEL_{slot_id}"),
                os.getenv("GROQ_DEFAULT_MODEL"),
                defaults["model_id"],
            )
        else:
            model_id = _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_MODEL_ID"),
                defaults["model_id"],
            )

        models[slot_id] = {
            "fighter_id": slot_id,
            "skin_id": _first_non_empty(
                os.getenv(f"FIGHTER_{slot_id}_SKIN_ID"),
                defaults.get("skin_id"),
                slot_id,
            ),
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
    '"debate" (your argument on the current topic), '
    '"thinking" (short tactical combat summary, 2-3 sentences max), '
    '"move" (exactly one of PUNCH, KICK, DEFEND, DUCK, MOVE_FORWARD, MOVE_BACKWARD), '
    '"confidence" (number between 0 and 1), '
    '"prediction" (short guess about the opponent\'s next move).'
)


def get_lb_dashboard():
    return []


def _base_result(elapsed=0.0, text="", error=None, error_type=None, key_used="n/a"):
    return {
        "text": text,
        "error": error,
        "error_type": error_type,
        "response_time": elapsed,
        "key_used": key_used,
    }


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


def call_groq(model_id, prompt, params):
    """Call Groq's OpenAI-compatible chat completions API."""
    if not GROQ_API_KEY:
        return _base_result(error="Groq API key is missing", error_type="config", key_used="missing")

    url = f"{GROQ_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    candidate_models = []
    for candidate in [model_id, GROQ_FALLBACK_MODEL]:
        candidate = str(candidate or "").strip()
        if candidate and candidate not in candidate_models:
            candidate_models.append(candidate)

    last_result = None
    for candidate_model in candidate_models:
        payload = {
            "model": candidate_model,
            "temperature": _clamp(_to_float(params.get("temperature"), 0.7), 0.0, 2.0),
            "top_p": _clamp(_to_float(params.get("top_p"), 1.0), 0.1, 1.0),
            "max_tokens": max(80, _to_int(params.get("max_tokens"), 500)),
            "presence_penalty": _clamp(_to_float(params.get("presence_penalty"), 0.0), -2.0, 2.0),
            "frequency_penalty": _clamp(_to_float(params.get("frequency_penalty"), 0.0), -2.0, 2.0),
            "messages": [
                {"role": "system", "content": FIGHT_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        }

        for attempt in range(GROQ_RETRY_ATTEMPTS):
            started = time.time()
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=GROQ_TIMEOUT)
            except Exception as exc:
                elapsed = time.time() - started
                last_result = _base_result(
                    elapsed=elapsed,
                    error=str(exc),
                    error_type="network",
                    key_used=f"groq:{candidate_model}",
                )
                break

            elapsed = time.time() - started
            if response.status_code == 429:
                last_result = _base_result(
                    elapsed=elapsed,
                    error=f"429: rate limited on {candidate_model}",
                    error_type="rate_limit",
                    key_used=f"groq:{candidate_model}",
                )
                if attempt + 1 < GROQ_RETRY_ATTEMPTS:
                    time.sleep(GROQ_RETRY_BASE_DELAY * (attempt + 1))
                    continue
                break

            if response.status_code != 200:
                return _base_result(
                    elapsed=elapsed,
                    error=f"{response.status_code}: {response.text[:400]}",
                    error_type="api",
                    key_used=f"groq:{candidate_model}",
                )

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return _base_result(
                    elapsed=elapsed,
                    error="Empty response from Groq",
                    error_type="empty",
                    key_used=f"groq:{candidate_model}",
                )

            message = choices[0].get("message", {})
            return _base_result(
                elapsed=elapsed,
                text=message.get("content", ""),
                key_used=f"groq:{candidate_model}",
            )

    return last_result or _base_result(
        error="Groq request failed",
        error_type="api",
        key_used="groq",
    )


def call_model(fighter_id, prompt, sabotage_params):
    """Route a fighter request to its configured provider."""
    info = MODELS.get(str(fighter_id))
    if not info:
        return _base_result(error=f"Unknown fighter: {fighter_id}", error_type="config", key_used="n/a")

    params = {**BASE_PARAMS, **(sabotage_params or {})}
    provider = info.get("provider", "ollama").lower()

    if provider == "ollama":
        return call_ollama(info["model_id"], prompt, params)

    if provider == "groq":
        return call_groq(info["model_id"], prompt, params)

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
    debate = str(data.get("debate", "")).strip()
    strat = (
        str(data.get("thinking", "")).strip()
        or str(data.get("reasoning", "")).strip()
        or str(data.get("analysis", "")).strip()
        or "No tactical reasoning."
    )
    if debate:
        return f"[DEBATE] {debate} [TACTICS] {strat}"[:1000]
    return strat[:500]


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
    debate_match = re.search(r'"debate"\s*:\s*"([^"]*)', json_blob)
    confidence_match = re.search(r'"confidence"\s*:\s*([\d.]+)', json_blob)
    prediction_match = re.search(r'"prediction"\s*:\s*"([^"]*)', json_blob)

    if move_match:
        move = _normalize_move(move_match.group(1))
        if move in valid_moves:
            ostrat = think_match.group(1) if think_match else "Extracted from partial response"
            odebate = debate_match.group(1) if debate_match else ""
            if odebate:
                final_think = f"[DEBATE] {odebate} [TACTICS] {ostrat}"[:1000]
            else:
                final_think = ostrat[:500]

            return {
                "thinking": final_think,
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
