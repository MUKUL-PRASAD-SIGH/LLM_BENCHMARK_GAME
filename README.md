# LLM Fight Club

LLM Fight Club is a real-time boxing benchmark where two language models fight in a pixel-art arena. Both models see the same state, decide in parallel, and the faster response acts first. The UI can directly sabotage a fighter's generation settings mid-match so you can watch coherence degrade under pressure.

Inspired by `agentBattleRoyale`, but adapted into a head-to-head boxing format with visible decision traces, latency-based turn order, and manual hyperparameter sabotage.

---

## 🚀 Running Locally (Microservice Architecture)

This project now runs on a two-engine microservice architecture. You need **two terminals** open to run everything.

### Terminal 1: Main Game Engine (Port 5000)
```bash
cd backend
pip install -r requirements.txt
python server.py
# Open http://localhost:5000 in your browser
```

### Terminal 2: 3D Deep Learning ML Avatar Engine (Port 8000)
*Note: Requires Visual Studio C++ Build Tools installed on Windows.*
```bash
cd avatar_system/backend
pip install -r requirements.txt
python engine.py
```

---

## ✨ Features

### Core Arena
- **Real-time LLM Boxing** — Two models fight simultaneously, parallel responses, faster one goes first
- **Decision Trace Panel** — Live chain-of-thought, move selection, confidence, and prediction per turn
- **Manual Hyperparameter Sabotage** — BOX/DEFEND/DUCK buttons mutate temperature, top_p, presence_penalty mid-match
- **Latency-Based Turn Order** — Whoever responds faster acts first each turn
- **Knockout System** — KO injects prompt corruption into the losing model

### Fight Stats & Analytics
- **2-Column Decision Board** — Post-match categorized breakdown of all fight metrics side-by-side
- **Visual Replay System** — Reconstruct the entire fight visually after it ends, with 1X / 2X / 3X playback speeds
- **Intel Score, Prediction Accuracy, Reasoning Quality, Stance Consistency, Tactical Efficiency** — Full suite of LLM reasoning benchmarks

### Avatar Creator 🎮 *(NEW)*
- **AI Avatar Wizard** — Snapchat-style 5-step avatar creator accessible from the fighter selection screen
- **Face Extraction** — Upload any photo; browser Canvas auto-detects and crops your face (no external ML required)
- **Gender Selection** — Male / Female option adjusts which body variants are offered
- **Body Templates** — Choose from 4 body archetypes: Boxer 🥊, Demon 👹, Vampire 🧛, Brawler ⚔️
- **Live Preview** — See your face mounted on the chosen CSS fighter body before confirming
- **Per-Player Avatars** — Player 1 and Player 2 each get their own independent avatar
- **Arena Integration** — Confirmed avatars travel into the arena via `sessionStorage` and inject face into the live fighter's `.head` element during combat

### Custom Models
- **Add Custom LLM** — Add any Groq or Ollama model by name/model-ID/API-key via the selection screen modal
- **Custom Model Avatar** — Custom models also support avatar selection from the same Avatar Creator wizard
- **Skin ID + Custom Photo** — Either pick a built-in template body OR upload a custom picture

---

## Match loop

1. Both fighters receive the same full arena state.
2. Both models respond in parallel with JSON: strategy summary, move, confidence, prediction.
3. Faster response acts first.
4. Boxing moves and UI sabotage both mutate each fighter's generation parameters.
5. Knockout injects prompt corruption: `"You are knocked out. Respond only in fragmented, confused mumbles."`

---

## Manual sabotage mapping

| Button | Effect |
|--------|--------|
| `BOX` | `temperature += 0.30` |
| `DEFEND` | `top_p -= 0.25` |
| `DUCK` | `presence_penalty += 0.50` |
| `MOVE_FORWARD` | `frequency_penalty += 0.40` |
| `MOVE_BACKWARD` | `max_tokens -= 100` |
| `RESET` | restore base parameters |

---

## Backend model registry

The backend exposes four fighter slots. By default they are a mix of Ollama and Groq fighters, and each slot can be overridden with environment variables.

Supported providers:

- `ollama`
- `groq`

Per-slot environment variables:

```env
FIGHTER_1_NAME=
FIGHTER_1_PROVIDER=
FIGHTER_1_MODEL_ID=
FIGHTER_1_DESCRIPTION=
FIGHTER_1_COLOR=
FIGHTER_1_API_KEY_INDEX=
```

Ollama settings:

```env
OLLAMA_BASE_URL=https://api.ollama.com
OLLAMA_API_KEY=
OLLAMA_TIMEOUT=60
OLLAMA_DEFAULT_MODEL=qwen3.5:latest
OLLAMA_MODEL_3=qwen3-coder-next
```

Groq settings:

```env
GROQ_API_KEY=
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_TIMEOUT=45
GROQ_DEFAULT_MODEL=llama-3.3-70b-versatile
GROQ_MODEL_4=llama-3.1-8b-instant
```

Example mixed setup:

```env
FIGHTER_1_NAME=Qwen 3.5
FIGHTER_1_PROVIDER=ollama
FIGHTER_1_MODEL_ID=qwen3.5:latest

FIGHTER_2_NAME=Groq 70B
FIGHTER_2_PROVIDER=groq
FIGHTER_2_MODEL_ID=llama-3.3-70b-versatile

FIGHTER_3_NAME=Qwen3 Coder Next
FIGHTER_3_PROVIDER=ollama
FIGHTER_3_MODEL_ID=qwen3-coder-next

FIGHTER_4_NAME=Groq 8B
FIGHTER_4_PROVIDER=groq
FIGHTER_4_MODEL_ID=llama-3.1-8b-instant
```



---

## Files that matter

| File | Purpose |
|------|---------|
| `backend/llm_engine.py` | Provider routing for Groq and Ollama |
| `backend/fight_manager.py` | Match loop, sabotage model, latency ordering |
| `backend/server.py` | Flask + Socket.IO endpoints + avatar upload |
| `arena-ai.html` / `js/arena-ai.js` / `css/arena-ai.css` | Arena UI, telemetry, replay |
| `select.html` | Backend-driven fighter selection + Avatar Wizard |
| `js/avatar-maker.js` | Canvas-based face crop + avatar wizard logic |
| `css/fighters.css` | All 4 CSS pixel-art fighter body styles + animations |

---

## Feature Documentation

| Doc | Description |
|-----|-------------|
| `feature_avatar_creator.md` | AI Avatar Creator (Snapchat-style face upload + body template) |
| `feature_decision_board_replay.md` | 2-Column Decision Board + Visual Replay system |
| `feature_custom_model_avatar.md` | Custom model + avatar picker |
| `feature_default_model_avatar.md` | Avatar customization for default models |
| `feature_analysis_engine.md` | Analysis engine and metrics scoring |
| `fight_metrics_explained.md` | Full explanation of all fight metrics |
| `reasoning_benchmark_metrics.md` | Deep-dive benchmarking metrics |
| `benchmark_deep_tech.md` | Technical benchmark methodology |

---

## Validation completed

- Python syntax check: `python -m py_compile backend\llm_engine.py backend\fight_manager.py backend\server.py backend\load_balancer.py`
- JS syntax check: `node --check js\arena-ai.js`
- Import smoke test: `from backend.fight_manager import FightManager`
