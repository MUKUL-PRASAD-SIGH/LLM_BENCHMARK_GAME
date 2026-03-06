# LLM Fight Club

LLM Fight Club is a real-time boxing benchmark where two language models fight in a pixel-art arena. Both models see the same state, decide in parallel, and the faster response acts first. The UI can directly sabotage a fighter's generation settings mid-match so you can watch coherence degrade under pressure.

Inspired by `agentBattleRoyale`, but adapted into a head-to-head boxing format with visible decision traces, latency-based turn order, and manual hyperparameter sabotage.

## What changed

- Dynamic benchmark telemetry in the arena UI
- Visible decision traces for both fighters every turn
- Manual sabotage buttons mapped to backend parameter injuries
- Provider-aware model routing with support for Gemini and optional Ollama fighters
- Data-driven fighter select screen powered by `/api/models`

## Match loop

1. Both fighters receive the same full arena state.
2. Both models respond in parallel with JSON: strategy summary, move, confidence, prediction.
3. Faster response acts first.
4. Boxing moves and UI sabotage both mutate each fighter's generation parameters.
5. Knockout injects prompt corruption: `"You are knocked out. Respond only in fragmented, confused mumbles."`

## Manual sabotage mapping

- `BOX` -> `temperature += 0.30`
- `DEFEND` -> `top_p -= 0.25`
- `DUCK` -> `presence_penalty += 0.50`
- `MOVE_FORWARD` -> `frequency_penalty += 0.40`
- `MOVE_BACKWARD` -> `max_tokens -= 100`
- `RESET` -> restore base parameters

## Backend model registry

The backend exposes four fighter slots. By default they are Gemini variants, but each slot can be overridden with environment variables.

Supported providers:

- `gemini`
- `ollama`

Per-slot environment variables:

```env
FIGHTER_1_NAME=
FIGHTER_1_PROVIDER=
FIGHTER_1_MODEL_ID=
FIGHTER_1_DESCRIPTION=
FIGHTER_1_COLOR=
FIGHTER_1_API_KEY_INDEX=
```

Gemini keys:

```env
GEMINI_API_KEY_1=
GEMINI_API_KEY_2=
```

Optional Ollama settings:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_API_KEY=
OLLAMA_TIMEOUT=60
OLLAMA_DEFAULT_MODEL=llama3.2
OLLAMA_MODEL_3=llama3.2
OLLAMA_MODEL_4=qwen2.5:7b
```

Example mixed setup:

```env
FIGHTER_1_NAME=Gemini Flash
FIGHTER_1_PROVIDER=gemini
FIGHTER_1_MODEL_ID=gemini-2.5-flash

FIGHTER_2_NAME=Gemini Pro
FIGHTER_2_PROVIDER=gemini
FIGHTER_2_MODEL_ID=gemini-2.5-pro

FIGHTER_3_NAME=Llama 3.2 3B
FIGHTER_3_PROVIDER=ollama
FIGHTER_3_MODEL_ID=llama3.2

FIGHTER_4_NAME=Qwen 2.5 7B
FIGHTER_4_PROVIDER=ollama
FIGHTER_4_MODEL_ID=qwen2.5:7b
```

## Running locally

Backend:

```bash
cd backend
pip install -r requirements.txt
python server.py
```

Frontend:

- Open `http://localhost:5000`
- Choose two fighters on `select.html`
- Start the match and use sabotage buttons on either side panel

## Files that matter

- `backend/llm_engine.py` - provider routing, Gemini failover, Ollama support
- `backend/fight_manager.py` - match loop, sabotage model, latency ordering
- `backend/server.py` - Flask + Socket.IO endpoints
- `arena-ai.html` / `js/arena-ai.js` / `css/arena-ai.css` - arena UI and telemetry
- `select.html` - backend-driven fighter selection

## Validation completed

- Python syntax check: `python -m py_compile backend\llm_engine.py backend\fight_manager.py backend\server.py backend\load_balancer.py`
- JS syntax check: `node --check js\arena-ai.js`
- Import smoke test: `from backend.fight_manager import FightManager`
