# Adding a New Model to LLM Fight Club

This document is the **definitive checklist** for adding a new LLM model to the system.
Follow every step carefully to ensure full integration with all analytics and debate features.

---

## ✅ DO ALL MODELS ALREADY HAVE DEBATE HISTORY + FULL FEATURES?

**YES — automatically**, because all fight features are attached to the `Fighter` class
in `fight_manager.py`, NOT to any individual model definition.

The `Fighter` class is instantiated generically from the `MODELS` registry. Every model you
add immediately inherits:

| Feature | Where it lives | Auto-inherited? |
|---|---|---|
| `debate_history` | `Fighter.__init__` | ✅ YES |
| `reward_history` | `Fighter.__init__` | ✅ YES |
| `last_reward` / `last_reward_reasons` | `Fighter.__init__` | ✅ YES |
| `total_reward` | `Fighter.__init__` | ✅ YES |
| `moves_made` | `Fighter.__init__` | ✅ YES |
| `response_times` | `Fighter.__init__` | ✅ YES |
| RL reward calculation | `FightManager._calculate_rewards()` | ✅ YES |
| Debate prompt injection | `FightManager.build_prompt()` | ✅ YES |
| Intelligence score | `FightAnalyzer.calculate_intelligence_score()` | ✅ YES |
| Leaderboard persistence | `FightAnalyzer.update_leaderboard()` | ✅ YES |
| Strategy heatmap | `FightAnalyzer.generate_strategy_heatmap()` | ✅ YES |

You only need to define the model's identity. The engine handles everything else.

---

## STEP 1 — Register the Model in `llm_engine.py`

Open `backend/llm_engine.py` and add a new entry to `DEFAULT_MODEL_SLOTS`:

```python
"5": {  # use the next available slot number (1–N)
    "name": "Your Model Display Name",
    "model_id": "actual-api-model-id",   # e.g. "llama-3.3-70b-versatile"
    "provider": "groq",                  # "groq" or "ollama"
    "skin_id": "5",                      # must match the slot number
    "description": "One-line description of this model's strengths.",
    "color": "#hex_color",               # used in UI for fighter color
},
```

### Supported Providers

| Provider | Value | Notes |
|---|---|---|
| Groq cloud API | `"groq"` | Requires `GROQ_API_KEY` in `.env` |
| Local Ollama | `"ollama"` | Requires Ollama running locally or cloud key |

> ⚠️ **IMPORTANT:** The slot number string key (`"5"` etc.) must be **unique** and **sequential**.
> Do NOT reuse an existing slot number without removing the old model first.

---

## STEP 2 — Add the Skin/UI Asset

Each fighter slot has a visual skin ID used in the frontend.

1. Add character sprite frames in `assets/images/fighters/fighter{N}/`
2. Ensure `skin_id` in `llm_engine.py` matches the folder/skin number you use in the arena HTML/JS

If you don't have a skin, reuse an existing one by pointing `skin_id` to `"1"`, `"2"`, etc.

---

## STEP 3 — Add Model to `.env` (Optional Override)

If you want to **override** the default model slot via environment variables (without editing code):

```env
FIGHTER_5_NAME=My Custom Model
FIGHTER_5_MODEL_ID=custom-model-id
FIGHTER_5_PROVIDER=groq
FIGHTER_5_SKIN_ID=5
```

This lets you swap models per-deployment without touching source code.

---

## STEP 4 — Add to Fighter Selection UI (`select.html`)

The `select.html` page lists the selectable fighters. Add your new slot to the fighter picker
so players can select it from the lobby screen.

Look for the existing fighter card structure and duplicate it with the new slot number.

---

## STEP 5 — Verify All Features Are Active (Checklist)

After adding the model, run a test fight and confirm all of these work:

- [ ] Fighter appears in the model selection screen (`select.html`)
- [ ] Fight launches and LLM responds with valid JSON (`thinking`, `debate`, `move`, `confidence`, `prediction`)
- [ ] Debate topic appears in the `[DEBATE]` field and changes each turn (no repetition)
- [ ] RL Score ticking up/down in the arena live UI during the fight
- [ ] Victory screen shows: Intelligence Score, RL Total Reward, Reasoning Quality, Thinking Consistency
- [ ] Strategy Heatmap generates on victory screen (requires matplotlib/seaborn working)
- [ ] Leaderboard updates in `data/leaderboard.json` after match ends
- [ ] Replay Timeline shows the model's full turn-by-turn decisions
- [ ] PDF Report includes all metrics, debate arguments, and RL reward reasons

---

## STEP 6 — Update `dumped_code.md`

Per project rules, after adding a new model, update `dumped_code.md` with:
- The new model slot entry
- Any new `.env` variable you introduced
- Notes on the model's behavior if tested

---

## ⚠️ Common Pitfalls When Adding Models

| Problem | Cause | Fix |
|---|---|---|
| Model always returns DEFEND | API error / bad model_id | Check terminal logs, verify `GROQ_API_KEY` |
| Debate field is empty | Model ignores `"debate"` key | Check that FIGHT_SYSTEM prompt includes `"debate"` |
| No heatmap on victory screen | model_id not found in report | Ensure `provider` key matches exactly |
| Model not on leaderboard | Fight ended before KO (draw) | Leaderboard updates only if `fm.game_over == True` |
| Repetitive debate arguments | Model has no frequency diversity | Increase `frequency_penalty` in `BASE_PARAMS` temporarily for that slot |

---

## Architecture Reference

```
llm_engine.py          → MODELS registry (identity only)
     ↓
fight_manager.py       → Fighter class (all state + history auto-attached)
     ↓
fight_manager.py       → FightManager (prompts, rewards, debate history injection)
     ↓
analysis_engine.py     → FightAnalyzer (scores, heatmaps, leaderboard)
     ↓
server.py              → REST + WebSocket API (served to frontend)
     ↓
arena-ai.js            → Renders everything live in the browser
```

> 💡 **Key insight:** You NEVER need to touch `Fighter`, `FightManager`, or `FightAnalyzer`
> to add a new model. Just register it in `DEFAULT_MODEL_SLOTS` and it inherits everything.
