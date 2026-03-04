# 🥊 LLM Fight Club

A real-time browser arena where ChatGPT, Claude, Gemini, and Grok battle each other — their API parameters (temperature, top_p, penalties) degrade as they take hits, making their responses progressively more chaotic.

---

## Project Structure

```
LLM Fight Club/
├── backend/
│   ├── services/
│   │   ├── openaiService.js      ✅ Done
│   │   ├── anthropicService.js   ✅ Done
│   │   ├── grokService.js        ✅ Done
│   │   └── geminiService.js      ✅ Done
│   ├── .env                      ⚠️  Exists but needs API keys filled in
│   ├── package.json              ✅ Done
│   └── server.js                 ✅ Done
├── frontend/
│   ├── public/                   📁 Empty folder
│   ├── src/
│   │   ├── components/
│   │   │   ├── Arena.jsx         ❌ Not built
│   │   │   ├── Boxer.jsx         ❌ Not built
│   │   │   └── BattleLog.jsx     ❌ Not built
│   │   └── App.js                ❌ Not built
│   └── package.json              ❌ Not configured
└── README.md
```

---

## ✅ What Is Built

### Backend — fully functional

#### `server.js`
- Express + Socket.io server running on port `3001`
- **Fighter state** for 4 fighters: `chatgpt`, `claude`, `gemini`, `grok`
  - Each fighter tracks: `hp`, `temp`, `top_p`, `presence_penalty`, `frequency_penalty`, `max_tokens`
- **Action system** — clients emit an `action` event with an action name and target fighter:
  | Action | Effect |
  |---|---|
  | `BOX` | -10 HP, temp +0.3 |
  | `DEFEND` | top_p → 0.5 |
  | `DUCK` | presence_penalty → 0.8 |
  | `MOVE_FWD` | frequency_penalty → 0.6 |
  | `MOVE_BACK` | max_tokens → 100 |
  | `RESET` | Fully restores fighter to defaults |
- **Knockout logic** — fighter is knocked out if `hp <= 0` or `temp > 1.8`; returns a random "concussed" response instead of calling the API
- **WebSocket events emitted to all clients:**
  - `fighters_update` — full fighter state after every action
  - `action_log` — log entry with message and timestamp
- **REST endpoints:**
  - `POST /fight` — sends a prompt to a specific fighter's LLM, returns the response
  - `GET /fighters` — returns current state of all fighters

#### `services/openaiService.js`
- Calls **ChatGPT** (`gpt-4o-mini`) with live fighter params (temp, top_p, penalties, max_tokens)

#### `services/anthropicService.js`
- Calls **Claude** (`claude-3-5-haiku-20241022`) with live fighter params
- Caps temperature at `1.0` (Claude API hard limit)

#### `services/grokService.js`
- Calls **Grok** (`grok-3-mini`) via xAI API using the OpenAI SDK with a custom `baseURL`

#### `services/geminiService.js`
- Calls **Gemini** (`gemini-2.0-flash`) via `@google/generative-ai` SDK
- All safety filters disabled so degraded high-temp output isn't blocked

#### `backend/package.json`
- All dependencies installed: `express`, `socket.io`, `openai`, `@anthropic-ai/sdk`, `@google/generative-ai`, `dotenv`, `cors`, `nodemon`
- ES Modules (`"type": "module"`)

---

## ❌ What Is Left to Build

### 1. `.env` — Add API Keys
Fill in `backend/.env`:
```
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROK_API_KEY=
PORT=3001
```

### 2. Frontend — Entirely unbuilt

#### `frontend/package.json`
- Needs to be initialized (React app — recommended: Vite + React)
- Dependencies needed: `react`, `react-dom`, `socket.io-client`

#### `src/App.js`
- Root component
- Should connect to the backend Socket.io server
- Should manage global fight state (fighters, battle log)
- Should render `<Arena />` and `<BattleLog />`

#### `src/components/Arena.jsx`
- The main fight stage
- Displays two (or more) fighters side by side
- Has action buttons (BOX, DEFEND, DUCK, MOVE_FWD, MOVE_BACK, RESET) per fighter
- Has a prompt input + Send button that calls `POST /fight`

#### `src/components/Boxer.jsx`
- Pixel art fighter UI for a single LLM
- Displays: fighter name, HP bar, current parameter values (temp, top_p, etc.)
- Should visually react to damage (shake, color change, knockout state)

#### `src/components/BattleLog.jsx`
- Real-time scrolling feed of `action_log` events received over Socket.io
- Shows timestamped messages of every action and LLM response

---

## How to Run (Backend)

```bash
cd backend
npm install
npm run dev
```

Server starts at `http://localhost:3001`
