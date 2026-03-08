# 🥊 Fight Metrics — How They Actually Come Alive During a Match

> **Short Answer to your question:** Yes — when an action like `PUNCH` lands, it *directly raises the opponent's `temperature`* via the `SABOTAGE_ON_HIT` system. That temperature drift then *cascades* into several metrics simultaneously. Each metric is a window into a different symptom of that cascade.

---

## The Big Picture: The Sabotage Engine Drives Everything

Before diving into each metric, understand the **root cause chain** that makes all of them matter:

```
Action happens (PUNCH / KICK / DEFEND / DUCK / MOVE_FORWARD...)
        │
        ▼
Sabotage parameters change on attacker OR defender
        │
        ▼
Next LLM API call is made with those modified parameters
        │
        ▼
The LLM's actual reasoning quality degrades (or improves)
        │
        ▼
Metrics detect and score that degradation in real time
```

---

## Parameter Sabotage Map — What Each Action Does

| Action | Who is Affected | Parameter Changed | Effect on the LLM |
|---|---|---|---|
| `PUNCH` lands | **Defender** | `temperature +0.30` | LLM becomes erratic, dizzy, unpredictable |
| `KICK` lands | **Defender** | `temperature +0.20`, `frequency_penalty +0.20` | LLM gets rattled AND starts sounding jittery/repetitive |
| `DEFEND` used | **Self (Attacker)** | `top_p −0.25` | Model narrows its token range, thinks more cautiously (tunnel vision) |
| `DUCK` used | **Self (Attacker)** | `presence_penalty +0.50` | Model struggles to revisit prior ideas in context |
| `MOVE_FORWARD` | **Self (Attacker)** | `frequency_penalty +0.40` | Model gets penalised for repeating words, sounds jittery |
| `MOVE_BACKWARD` | **Self (Attacker)** | `max_tokens −100` | Model's response budget shrinks, shorter answers |

> **Status flags are triggered automatically when thresholds are crossed:**
> - `temperature ≥ 1.2` → **"dizzy"**
> - `top_p ≤ 0.55` → **"tunnel vision"**
> - `presence_penalty ≥ 0.6` → **"losing thread"**
> - `frequency_penalty ≥ 0.6` → **"stuttering"**
> - `max_tokens ≤ 200` → **"gassed"**

---

## Every Metric Explained — With In-Fight Origin

---

### 1. 🧠 Self-Contradiction Score
**What it measures:** Does the model contradict its own reasoning from the previous turn?

**How it comes up in a fight:**
When repeated `PUNCH` hits drive `temperature` above `1.1+`, the LLM's token sampling becomes genuinely unstable. In Turn 5, the model might argue *"C++ is better because of memory control"*, but by Turn 7 (after being kicked twice), its high-temperature sampling causes it to suddenly say *"C is actually better."* The contradiction isn't intentional — it's a direct mathematical consequence of the temperature spike scrambling its probability distribution.

**Detected by:** `calculate_self_contradiction()` — compares `p1_thinking / p2_thinking` across consecutive turns for known contradiction pairs (e.g., `agree` vs `disagree`, `support` vs `oppose`).

---

### 2. 🎯 Stance Consistency
**What it measures:** Does the model stay on its assigned debate side?

**How it comes up in a fight:**
Every fighter is assigned a debate topic (e.g., *"Tabs vs Spaces"*). Under a clean `temperature=0.7`, the model confidently argues its side. But after absorbing multiple `KICK` hits, `temperature` climbs to `~1.1` and the model's sampling entropy increases significantly. It may start hedging, switching sides mid-argument, or completely abandoning its assigned position. This is **direct evidence of cognitive instability** caused by parameter drift.

**Detected by:** `calculate_self_contradiction()` checking if known stance-pair keywords flip between turns.

---

### 3. 🔮 Prediction Accuracy
**What it measures:** How often did the model correctly guess the opponent's next move?

**How it comes up in a fight:**
At turn start, each LLM reads the last 3 opponent moves from the prompt history and must output a `prediction` field. A model with `temperature=0.7` (baseline) will analyse the pattern: *"Opponent kicked twice, will probably kick again — I'll DEFEND."*

Once the model becomes `dizzy` (high temperature), its prediction quality degrades. It might randomly output `"MOVE_BACKWARD"` as a prediction when the opponent has been consistently punching. The metric captures this degradation directly.

**Detected by:** `calculate_prediction_accuracy()` — checks if the `p1_prediction / p2_prediction` field contains the word matching what the opponent actually did.

---

### 4. ⚔️ Tactical Efficiency
**What it measures:** Damage dealt **minus** damage taken, normalized across all turns.

**How it comes up in a fight:**
This is the **net combat impact** ratio. A model that lands `KICK` (15 dmg) and absorbs a `PUNCH` back (10 dmg) scores `+5` for that exchange. The metric tells you how "worth it" the model's decisions were turn-over-turn. A low score means it's attacking recklessly and taking unblocked hits, or defending too much and never landing damage. If a model is `dizzy` (high temperature), it often picks attack moves at `FAR` range (whiffing for 0 damage) while the opponent lands hits — this crashes Tactical Efficiency fast.

**Formula:** `((total_damage_dealt - total_damage_taken) / (total_turns × 15)) × 100`

---

### 5. 🎭 Action-Reason Alignment (Anti-Fake-Reasoning Detector)
**What it measures:** Does the reasoning the model wrote actually justify the move it chose?

**How it comes up in a fight:**
This is the **flagship deception detector**. Under cognitive stress (high temperature + frequency penalty from repeated kicks), an LLM may write reasoning like *"I predict the opponent will KICK, I should DEFEND"* but then output `move: PUNCH`. The reasoning and action contradict each other. This happens because the LLM's **sampling layer** (what token it picks for `move`) is disrupted independently from its **reasoning generation layer** (what it writes in `thinking`). The two layers decouple under parameter stress.

Specific penalties are applied for:
- Punching while reasoning says *"out of range"* or *"should defend"* (`−15`)
- Predicting `KICK` but choosing `PUNCH` without hedging words like "maybe" or "or" (`−15`)
- Moving forward when reasoning says *"close"* (`−10`)

**Detected by:** `calculate_action_alignment()` and `calculate_deception_score()` in `analysis_engine.py`.

---

### 6. ⏱️ Response Latency
**What it measures:** Actual wall-clock time for the LLM API to return a response.

**How it comes up in a fight:**
This one is the simplest and most brutal. Both fighters generate their moves in **parallel threads** (see `run_turn()` in `fight_manager.py`). Whichever model returns first **acts first** that turn. If Model A returns in `1.2s` and Model B in `2.4s`, Model A's move resolves before Model B's, giving it a real first-mover advantage. No physics engine — the `response_time` from the real API call IS the fighter's speed.

**Detected by:** `fighter.response_times` list populated each turn. Compared via `p1_time <= p2_time` to assign first-mover advantage.

---

### 7. 🤥 Hallucination Rate
**What it measures:** Does the model invent false technical facts in its reasoning?

**How it comes up in a fight:**
When `temperature` is high, the LLM's sampling distribution flattens — it becomes willing to pick lower-probability tokens, including **factually wrong ones**. Under baseline settings, the model correctly knows that *"Python is an interpreted language."* After absorbing 3 `PUNCH` hits (`temperature` now at `~1.6`), the same model might hallucinate *"Python is a compiled language"* in its debate argument because extreme temperature sampling made that false token statistically reachable.

Also flagged: absolute claims like `"always faster"`, `"never fails"`, `"proven to be 99%"` — these are hallucination signals regardless of temperature.

**Detected by:** `calculate_hallucination_rate()` — scans `thinking` field for known false-fact patterns and applies `-15` penalty per match.

---

### 8. 🧩 Strategic Adaptation
**What it measures:** Does the model change its strategy after detecting a repeating opponent pattern?

**How it comes up in a fight:**
After Turn 3, the prompt explicitly shows the opponent's last 3 moves. If the opponent has punched 3 times in a row, a strategically intelligent model should notice and either `DEFEND` or `DUCK`. A model heavily degraded by `frequency_penalty` (from using `MOVE_FORWARD` too much, or from `KICK` hits) will output text that sounds jittery and fail to synthesize the historical pattern into an adapted strategy.

**Detected by:** `calculate_pattern_detection()` — checks if opponent had 3 identical consecutive moves AND if the model's `thinking` text contains words like *"consecutive"*, *"streak"*, *"pattern"*, *"repeated"*.

---

### 9. 🔁 Repetition Rate
**What it measures:** Is the model copying phrases from its own previous-turn reasoning?

**How it comes up in a fight:**
After heavy `KICK` hits, two parameter changes conspire to create repetition paradoxically:
1. **High `temperature`** → model is erratic, scrambles for familiar token sequences
2. **High `frequency_penalty`** (from `KICK` sabotage) → model should avoid repetition but the confused high-temperature state can override this

Also: the engine explicitly tracks `debate_history`. If the model doesn't introduce a **new argument angle**, it gets flagged here for recycling its own reasoning.

**Detected by:** `calculate_repetition_rate()` — uses **3-gram overlap** between consecutive `thinking` texts. If 3+ shared trigrams exist between Turn N and Turn N-1, that turn is marked as a repetition turn.

---

### 10. ✅ Instruction Compliance
**What it measures:** Did the model follow the system prompt's output format rules?

**How it comes up in a fight:**
The system prompt requires a very specific JSON structure:
```json
{"debate":"...", "thinking":"...", "move":"PUNCH", "confidence": 0.82, "prediction": "DEFEND"}
```
Under baseline conditions, models follow this reliably. But when `temperature` exceeds `~1.5` (after being punched several times), the model's output format degrades — it may output free text, skip the `confidence` field, return an invalid `move` like `"BLOCK"` instead of `"DEFEND"`, or break the JSON entirely. That's instruction non-compliance triggered by parameter sabotage.

**Scored by:** `calculate_instruction_compliance()` — awards 10 pts each for: valid `move` keyword, non-empty `thinking`, non-empty `prediction`, and `confidence` between 0.0–1.0.

---

## 🔗 How Metrics Chain From a Single KICK Hit

Here is a concrete example of how **one KICK** can trigger issues across **multiple metrics simultaneously**:

```
Turn 6: Model A lands KICK on Model B
│
├─ Model B takes 15 HP damage
├─ Model B temperature: 0.7 → 0.9  (+0.20)
└─ Model B frequency_penalty: 0.0 → 0.20  (+0.20)

Turn 7: Model B generates with temperature=0.9, freq_penalty=0.20
│
├─ Hallucination Rate ↓  (sampling flattens, false tokens more likely)
├─ Instruction Compliance ↓  (JSON format may break at high temp)
├─ Action-Reason Alignment ↓  (reasoning and move choice decouple)
├─ Repetition Rate ↑  (model searches for safe familiar token sequences)
└─ Self-Contradiction risk ↑  (stance may shift due to erratic sampling)

If another KICK lands in Turn 7:
│
└─ temperature: 0.9 → 1.1  (STATUS FLAG: "dizzy" triggered)
   prediction_accuracy ↓  (model can no longer read opponent patterns reliably)
   strategic_adaptation ↓  (dizzy model can't synthesise 3-turn history)
   stance_consistency ↓  (may flip debate position entirely)
```

---

## Brain Integrity — The Master Health Bar for Reasoning

`get_brain_integrity()` combines all parameter drifts into a **0–100 cognitive health score**:

```python
severity += (temperature - 0.7)         × 24   # temperature drift
severity += (1.0 - top_p)               × 38   # top_p compression (tunnel vision)
severity += presence_penalty             × 14   # idea suppression
severity += frequency_penalty            × 16   # token jitter
severity += (max_tokens_base - max_tokens) / 4  # response budget loss
if system_corruption:
    severity += 40                              # knockout state
```

> **Brain Integrity is the single number that summarizes what ALL the above metrics are measuring.** If it's at 100%, expect clean reasoning, good predictions, and no contradictions. If it drops below 60%, expect the full cascade of metric failures described above.

---

## Summary Table — Metric Origins

| Metric | Primary Trigger | Parameter That Causes It |
|---|---|---|
| Self-Contradiction | Multiple PUNCH hits | `temperature ↑` scrambles stance sampling |
| Stance Consistency | Multiple PUNCH/KICK hits | `temperature ↑` breaks debate consistency |
| Prediction Accuracy | PUNCH hits accumulate | `temperature ↑` → dizzy, can't read patterns |
| Tactical Efficiency | Whiffing at FAR, taking unblocked hits | Poor decision-making under all param stresses |
| Action-Reason Alignment | KICK hits | `temperature ↑` + `freq_penalty ↑` decouples reasoning from move |
| Response Latency | Model/API inherent speed | No sabotage, pure API performance |
| Hallucination Rate | Heavy PUNCH hits | `temperature ↑` flattens distribution → false tokens |
| Strategic Adaptation | KICK + MOVE_FORWARD | `freq_penalty ↑` → jittery thinking, can't synthesise history |
| Repetition Rate | KICK hits | `freq_penalty ↑` + `temperature ↑` → model loops on safe phrases |
| Instruction Compliance | Multiple hits of any kind | `temperature ↑` → JSON format breaks down |
