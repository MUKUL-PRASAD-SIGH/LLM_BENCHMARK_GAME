"""
LLM Engine - Handles API calls to Gemini models.
Measures response time and applies hyperparameter sabotage.
Uses LoadBalancer for intelligent API key routing & failover.
"""

import time
import json
import re
import requests
import os
from dotenv import load_dotenv
from load_balancer import LoadBalancer

load_dotenv()

GEMINI_API_KEYS = [
    os.getenv('GEMINI_API_KEY_1', ''),
    os.getenv('GEMINI_API_KEY_2', ''),
]

# Initialize the global load balancer
lb = LoadBalancer(
    keys=GEMINI_API_KEYS,
    max_concurrent_per_key=3,
    base_cooldown=5.0,
    max_cooldown=120.0,
)

def get_lb_dashboard():
    """Return load balancer health dashboard data."""
    return lb.get_dashboard()

# Model Registry — all 4 fighters use Gemini models (both keys confirmed working)
MODELS = {
    '1': {
        'name': 'Gemini 2.5 Flash',
        'model_id': 'gemini-2.5-flash',
        'provider': 'gemini',
        'api_key_index': 0,
        'description': 'Fast & agile. Quick decisions, lightning reflexes.',
        'color': '#4285f4',
    },
    '2': {
        'name': 'Gemini 2.5 Pro',
        'model_id': 'gemini-2.5-pro',
        'provider': 'gemini',
        'api_key_index': 1,
        'description': 'Strategic powerhouse. Deep reasoning, calculated strikes.',
        'color': '#ea4335',
    },
    '3': {
        'name': 'Gemini 2.0 Flash',
        'model_id': 'gemini-2.0-flash',
        'provider': 'gemini',
        'api_key_index': 0,
        'description': 'Previous gen speed demon. Proven and reliable.',
        'color': '#7c3aed',
    },
    '4': {
        'name': 'Gemini 2.5 Flash-Lite',
        'model_id': 'gemini-2.5-flash-preview-04-17',
        'provider': 'gemini',
        'api_key_index': 1,
        'description': 'Experimental preview build. Unpredictable edge.',
        'color': '#cc1111',
    },
}

BASE_PARAMS = {
    'temperature': 0.7,
    'top_p': 1.0,
    'presence_penalty': 0.0,
    'frequency_penalty': 0.0,
    'max_tokens': 256,
}

FIGHT_SYSTEM = (
    "You are a boxer AI in a fighting game. You MUST respond with ONLY a valid JSON object. "
    "No other text before or after. The JSON must have these keys: "
    '"thinking" (string, 1-2 sentences of strategy), '
    '"move" (string, exactly one of: PUNCH, KICK, DEFEND, DUCK, MOVE_FORWARD, MOVE_BACKWARD), '
    '"confidence" (number between 0 and 1), '
    '"prediction" (string, what you think opponent will do). '
    'Example: {"thinking":"Close range, time to strike.","move":"PUNCH","confidence":0.8,"prediction":"DEFEND"}'
)


def call_gemini(model_id, prompt, params, api_key):
    """
    Call Google Gemini API via REST.
    The api_key is managed by the LoadBalancer — success/failure is reported
    back so the LB can adapt routing decisions.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:generateContent?key={api_key}"
    )

    gen_config = {
        'temperature': min(2.0, max(0.0, params.get('temperature', 0.7))),
        'topP': min(1.0, max(0.1, params.get('top_p', 1.0))),
        'maxOutputTokens': max(80, int(params.get('max_tokens', 256))),
    }

    pp = params.get('presence_penalty', 0.0)
    fp = params.get('frequency_penalty', 0.0)
    if pp != 0.0:
        gen_config['presencePenalty'] = min(2.0, max(-2.0, pp))
    if fp != 0.0:
        gen_config['frequencyPenalty'] = min(2.0, max(-2.0, fp))

    payload = {
        'system_instruction': {'parts': [{'text': FIGHT_SYSTEM}]},
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': gen_config,
    }

    start_time = time.time()
    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=45)
            elapsed = time.time() - start_time

            if resp.status_code == 429:
                # Report rate-limit to load balancer (triggers cooldown)
                lb.report_rate_limit(api_key)

                if attempt < max_retries:
                    # Try to get a different key from the balancer
                    new_key = lb.acquire_key()
                    if new_key and new_key != api_key:
                        print(f"  [LB FAILOVER] {model_id} → key ...{api_key[-6:]} rate-limited, "
                              f"switching to ...{new_key[-6:]} (attempt {attempt+1})")
                        lb.release_key(api_key)
                        api_key = new_key
                        url = (
                            f"https://generativelanguage.googleapis.com/v1beta/models/"
                            f"{model_id}:generateContent?key={api_key}"
                        )
                    else:
                        if new_key:
                            lb.release_key(new_key)
                        wait = 2 ** (attempt + 1)
                        print(f"  [GEMINI 429] {model_id} → rate limited, retry in {wait}s "
                              f"(attempt {attempt+1})")
                        time.sleep(wait)
                    continue

            if resp.status_code != 200:
                err = resp.text[:400]
                print(f"  [GEMINI ERR] {model_id} → {resp.status_code}: {err}")
                lb.report_error(api_key)
                return {'text': '', 'error': f"{resp.status_code}: {err}",
                        'response_time': elapsed, 'key_used': f'...{api_key[-6:]}'}

            data = resp.json()
            cands = data.get('candidates', [])
            if not cands:
                reason = data.get('promptFeedback', {}).get('blockReason', 'none')
                print(f"  [GEMINI] {model_id} → blocked: {reason}")
                lb.report_success(api_key, elapsed)  # API worked, content was blocked
                return {'text': '', 'error': f"Blocked: {reason}",
                        'response_time': elapsed, 'key_used': f'...{api_key[-6:]}'}

            parts = cands[0].get('content', {}).get('parts', [])
            if not parts:
                finish = cands[0].get('finishReason', '?')
                print(f"  [GEMINI] {model_id} → empty, finish={finish}")
                lb.report_success(api_key, elapsed)
                return {'text': '', 'error': f"Empty (finish={finish})",
                        'response_time': elapsed, 'key_used': f'...{api_key[-6:]}'}

            text = parts[0].get('text', '')
            print(f"  [GEMINI OK] {model_id} → {len(text)} chars, {elapsed:.1f}s "
                  f"(key ...{api_key[-6:]})")
            lb.report_success(api_key, elapsed)
            return {'text': text, 'error': None,
                    'response_time': elapsed, 'key_used': f'...{api_key[-6:]}'}

        except Exception as e:
            elapsed = time.time() - start_time
            lb.report_error(api_key)
            if attempt < max_retries:
                print(f"  [GEMINI EXC] {model_id} → {e}, retrying...")
                time.sleep(2)
                continue
            print(f"  [GEMINI EXC] {model_id} → {e}")
            return {'text': '', 'error': str(e),
                    'response_time': elapsed, 'key_used': f'...{api_key[-6:]}'}

    return {'text': '', 'error': 'Max retries exceeded',
            'response_time': time.time() - start_time, 'key_used': f'...{api_key[-6:]}'}


def call_model(fighter_id, prompt, sabotage_params):
    """
    Route to the correct provider using the LoadBalancer for key selection.
    The preferred_index hint comes from the model config, but the LB will
    override it if that key is unhealthy.
    """
    info = MODELS.get(fighter_id)
    if not info:
        return {'text': '', 'error': f'Unknown fighter: {fighter_id}', 'response_time': 0}

    params = {**BASE_PARAMS, **sabotage_params}
    preferred_idx = info.get('api_key_index', 0)

    # Acquire a key from the load balancer (health-aware)
    key = lb.acquire_key(preferred_index=preferred_idx)
    if not key:
        return {'text': '', 'error': 'No API keys available', 'response_time': 0}

    try:
        result = call_gemini(info['model_id'], prompt, params, key)
        return result
    finally:
        # Always release the key back to the pool
        lb.release_key(key)


def parse_llm_response(text):
    """Parse the LLM's JSON response. Handles truncated JSON, markdown, etc."""
    valid = ['PUNCH', 'KICK', 'DEFEND', 'DUCK', 'MOVE_FORWARD', 'MOVE_BACKWARD']

    if not text or not text.strip():
        return _default('No response from model')

    clean = text.strip()

    # Remove <think> tags (some models use these)
    clean = re.sub(r'<think>.*?</think>', '', clean, flags=re.DOTALL).strip()
    # Remove markdown fences
    clean = re.sub(r'```(?:json)?\s*', '', clean).strip()

    # Find JSON object
    start = clean.find('{')
    if start == -1:
        return _fallback(clean, valid, text)

    json_str = clean[start:]

    # Try direct parse
    try:
        data = json.loads(json_str)
        return _from_data(data, valid, text)
    except json.JSONDecodeError:
        pass

    # Try closing truncated JSON
    for fix in ['"}', '"}', '}']:
        try:
            data = json.loads(json_str + fix)
            return _from_data(data, valid, text)
        except json.JSONDecodeError:
            continue

    # Regex extraction from partial JSON
    move_m = re.search(r'"move"\s*:\s*"(\w+)"', json_str)
    think_m = re.search(r'"thinking"\s*:\s*"([^"]*)', json_str)
    conf_m = re.search(r'"confidence"\s*:\s*([\d.]+)', json_str)
    pred_m = re.search(r'"prediction"\s*:\s*"([^"]*)', json_str)

    if move_m:
        mv = move_m.group(1).upper()
        if mv in valid:
            return {
                'thinking': think_m.group(1) if think_m else 'Extracted from partial response',
                'move': mv,
                'confidence': float(conf_m.group(1)) if conf_m else 0.5,
                'prediction': pred_m.group(1) if pred_m else 'Unknown',
                'raw': text,
            }

    return _fallback(clean, valid, text)


def _from_data(data, valid, raw):
    mv = str(data.get('move', 'DEFEND')).upper().strip()
    if mv not in valid:
        mv = 'DEFEND'
    return {
        'thinking': str(data.get('thinking', ''))[:500] or 'No reasoning.',
        'move': mv,
        'confidence': min(1.0, max(0.0, float(data.get('confidence', 0.5)))),
        'prediction': str(data.get('prediction', 'Unknown'))[:200],
        'raw': raw,
    }


def _fallback(clean, valid, raw):
    upper = clean.upper()
    for m in ['MOVE_FORWARD', 'MOVE_BACKWARD', 'KICK', 'PUNCH', 'DUCK', 'DEFEND']:
        if m in upper:
            return {
                'thinking': clean[:300],
                'move': m,
                'confidence': 0.3,
                'prediction': 'Unknown',
                'raw': raw,
            }
    return _default(clean[:300])


def _default(msg):
    return {
        'thinking': msg,
        'move': 'DEFEND',
        'confidence': 0.1,
        'prediction': 'Unknown',
        'raw': '',
    }
