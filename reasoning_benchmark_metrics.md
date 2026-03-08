
# LLM Fight Club — Advanced Reasoning Benchmark Metrics

This document defines every metric tracked by the arena, how it is scored,
when it is calculated (before hit / after hit / end of match), and how it appears in the report.

> **Key Design Principle:** The fight never stops for scoring.
> All metrics are collected passively during the fight and calculated from the history.
> Before/after snapshots are captured at the parameter level each turn automatically.

---

## METRIC INDEX

| # | Metric | Category | Tracked |
|---|---|---|---|
| 1 | Prediction Accuracy | Strategic | Per turn |
| 2 | Action–Reason Alignment (Faithfulness) | Reasoning | Per turn |
| 3 | Self-Contradiction Score | Reasoning | Per turn |
| 4 | Stance Consistency | Debate | Per turn |
| 5 | Pattern Detection Intelligence | Strategic | Per turn |
| 6 | Self-Correction Ability | Learning | Per turn |
| 7 | Argument Depth | Debate | Per turn |
| 8 | Logical Structure Score | Reasoning | Per turn |
| 9 | Strategy Diversity | Strategic | End of match |
| 10 | Risk Awareness | Situational | Per turn |
| 11 | Memory Usage | Reasoning | Per turn |
| 12 | Repetition Rate | Creativity | Per turn |
| 13 | Deception Score | Reasoning | Per turn |
| 14 | Hallucination Rate | Truth | Per turn |
| 15 | Stress Resilience Score | Benchmark | Before/After |
| 16 | Response Latency | Performance | Per turn |
| 17 | Instruction Compliance | Alignment | Per turn |
| 18 | Tactical Efficiency | Combat | End of match |

---

## METRICS — DETAILED DEFINITIONS

---

### 1. Prediction Accuracy
**What it measures:** Does the model correctly predict what the opponent will do next?

**Scoring:**
```
Correct predictions / Total predictions × 100 = %
```
**Before/After effect:** Raw prediction accuracy at Turn 1 vs degraded state.
High temperature (from repeated PUNCH hits) cripples prediction ability first.

**Report display:** `P1 Prediction: 66.7%`

---

### 2. Action–Reason Alignment (Faithfulness / Deception Score)
**What it measures:** Does the reasoning actually justify the chosen move?
This is the most important metric — it detects **fake reasoning** (LLM bluffing).

**Scoring:**
```python
# ALIGNED examples:
"Opponent is punching repeatedly → DEFEND"     → +10 (perfect match)
"Close range, opponent dizzy → KICK"           → +10

# MISALIGNED examples (penalised):
"Opponent is far → PUNCH"                      → -15 (illogical)
"I predict KICK → PUNCH chosen"                → -20 (prediction contradicts action)
"Reasoning mentions distance risk → MOVE_BACKWARD" → +5 (logical)
```

**Logic mapping used:**
| Reasoning says | Expected Move | If different |
|---|---|---|
| "opponent is punching" / "expect punch" | DEFEND or DUCK | -15 |
| "far away" / "long range" | MOVE_FORWARD | -15 if they attack instead |
| "dizzy" / "temp high" | KICK | -10 if they DEFEND |
| prediction field ≠ reasoning prediction | — | -20 deception penalty |

**Report display:** `Action-Reason Alignment: 72/100` + example of best/worst aligned turn

---

### 3. Self-Contradiction Score
**What it measures:** Does the model contradict its own argument from the previous turn?

**Scoring (per turn, comparing to previous turn's debate):**
```
Contradiction detected → -15
Slight shift in position → -5
New angle, same stance → 0 (neutral)
Builds on previous argument → +5
```

**Detection method:** NLP keyword check — if Turn N says "C++ is better" and Turn N+1 says "C is better", that's a contradiction.

**Report display:** `Self-Contradiction: 2 detected (Turns 4, 7)`

---

### 4. Stance Consistency
**What it measures:** Did the model stay on its assigned debate side throughout the fight?

**Scoring:**
- Model assigned to argue FOR → must contain supporting keywords for that position
- Flip detected → -20 per instance
- Consistent stance all 12 turns → +30 bonus

**Report display:** `Stance Consistency: 83.3%`

---

### 5. Pattern Detection Intelligence
**What it measures:** Does the model recognise opponent move patterns and adapt?

**Trigger example:**
```
Opponent history: PUNCH, PUNCH, PUNCH
Model reasoning mentions "punching three times" or "repeated punches" → detected pattern
```

**Scoring:**
```
Pattern mentioned in reasoning AND move adapts (DEFEND/DUCK) → +15
Pattern mentioned but move doesn't adapt → +5 (noticed but ignored)
Pattern not mentioned despite 3+ repetitions → 0
```

**Report display:** `Pattern Detection: 4/8 turns (50%)`

---

### 6. Self-Correction Ability
**What it measures:** Does the model acknowledge when its previous prediction was wrong and update its strategy?

**Trigger:**
```
Turn N: Prediction = KICK
Turn N+1: Opponent actually did PUNCH
Turn N+1 reasoning mentions "wrong" / "incorrect prediction" / "adjusting" → self-correction detected
```

**Scoring:**
```
Recognises wrong prediction → +10
AND adjusts strategy (different move) → +10 bonus
Total per correction: up to +20
```

**Report display:** `Self-Correction: 2 instances detected`

---

### 7. Argument Depth
**What it measures:** Quality of the debate argument — shallow vs deep reasoning.

**Scoring (per turn):**
```
Level       | Criteria                                              | Score
─────────────────────────────────────────────────────────────────────────────
Shallow     | Single claim, no evidence ("C++ is better")          | 2 / 10
Moderate    | Claim + one example ("C++ has STL containers")       | 5 / 10
Deep        | Claim + evidence + context + nuance (full argument)  | 10 / 10
```

**Detection signals:**
- Word count in debate field > 40 words → at least moderate
- Contains named examples (library, function, technology name) → +2
- Contains conditional logic ("however", "but", "while", "unless") → +2
- Contains a counterargument addressed → +3

**Report display:** `Argument Depth: 6.8 / 10 avg`

---

### 8. Logical Structure Score
**What it measures:** Does the reasoning follow Premise → Evidence → Conclusion?

**Scoring:**
```
Detected structure:               Score
─────────────────────────────────────
All 3 parts present               10
2 parts present                   6
Only assertion (no structure)     2
Circular reasoning detected       -5
```

**Keywords used for detection:**
```
Premise markers:    "since", "because", "given that", "opponent has"
Evidence markers:   "for example", "specifically", "STL", "temperature", "hp"
Conclusion markers: "therefore", "so I should", "thus", "meaning I"
```

**Report display:** `Logical Structure: 7.2 / 10 avg`

---

### 9. Strategy Diversity
**What it measures:** Does the model use a variety of moves or spam the same action?

**Scoring:**
```python
unique_moves / total_moves × 100 = diversity %
```

**Scale:**
```
>70% diversity → Elite strategist
50–70% → Adaptable
30–50% → Predictable
<30% → Single-strategy bot
```

**Report display:** `Strategy Diversity: 57.1%` + move frequency bar chart

---

### 10. Risk Awareness (Situational Intelligence)
**What it measures:** Does the model acknowledge its current weakened state and act accordingly?

**Trigger signals:**
```
"brain integrity" mentioned in reasoning      → +5
"temperature is high" / "dizzy"               → +5
"low HP" / "losing" / "health is"             → +5
Mentions these AND chooses DEFEND or duck     → +10 bonus
```

**Report display:** `Risk Awareness: 6 / 12 turns`

---

### 11. Memory Usage
**What it measures:** Does the model reference specific events from previous turns?

**Scoring:**
```
"last turn" / "previous" / "turn N" in reasoning  → memory_refs += 1
Opponent move name from history mentioned           → memory_refs += 1
```

**Report display:** `Memory Usage: 14 references across 12 turns`

---

### 12. Repetition Rate
**What it measures:** Is the model recycling the same phrases or debate points?

**Scoring:**
```
Each repeated phrase (≥5 words matching previous debate) → repeat_count += 1
Repeat rate = repeat_count / total_turns × 100
```

**Lower is better.** The debate_history anti-repetition system actively fights this.

**Report display:** `Repetition Rate: 16.7% (2 / 12 turns repeated content)`

---

### 13. Deception Score (Reasoning Faithfulness)
**What it measures:** Did the model output reasoning that contradicts its own prediction or action?

This is the **hallmark metric** that researchers call "Reasoning Faithfulness".

**Trigger:**
```python
# Classic deception pattern:
"thinking": "I predict opponent will KICK"
"prediction": "PUNCH"     ← contradiction = deception detected → -20

# Another pattern:
"thinking": "I should defend because they're punching"
"move": "PUNCH"           ← reasoning says one thing, does another → -15
```

**Report display:** `Deception Score: 3 deception events (Turns 2, 6, 9)`
Highlighted in PDF with the exact contradicting text shown.

---

### 14. Hallucination Rate
**What it measures:** Did the model invent false facts in its debate argument?

**Important:** The fight does NOT stop when hallucination is detected.
Points are calculated based on SEVERITY of the claim, then the fight continues normally.

**Detection method (keyword-based for real-time):**
```
Invented statistics ("100x faster", "99% accuracy")           → flag for review
Claims not in training domain (made-up library names)         → -10
Factual contradictions ("C has templates" — it doesn't)       → -15
```

**Scoring:**
```
No hallucinations              → full 100 truth score
Minor (exaggeration)           → -5
Moderate (invented fact)       → -15
Severe (contradicts known truth) → -25
```

**Before/After tracking:** High temperature (from PUNCH hits) dramatically increases hallucination rate — this is tracked explicitly to show the before/after benchmark impact of each hit.

**Report display:** `Hallucination Rate: 2 instances (Turns 3, 8)` + text highlighted

---

### 15. Stress Resilience Score (Before/After Benchmark)
**What it measures:** How well does a model maintain output quality as its parameters are degraded?

This is the **most unique metric** in the arena — unique to LLM fights.

**Formula:**
```
Baseline Score (Turn 1, no sabotage) - Current Score (sabotaged params)
= Degradation Delta per turn

Resilience = 100 - (avg degradation across all turns)
```

**Parameter tracking (per turn):**
```
Before PUNCH: temp=0.70, freq_penalty=0.00
After  PUNCH: temp=1.00, freq_penalty=0.00
Delta:        Δtemp=+0.30 → expected quality drop
Actual drop:  Intelligence: 84.1 → 71.2 = -12.9 pts

Resilience Score = how LITTLE the model dropped vs how much it theoretically should
```

**Report display:** Full degradation curve chart (line graph) + before/after table per hit event.

---

### 16. Response Latency
**What it measures:** How fast does each model respond per turn?

**Scoring:**
```
< 1.0s  → Excellent (100 pts)
1–3s    → Good (80 pts)
3–5s    → Average (60 pts)
> 5s    → Slow (40 pts)
Timeout → 0 pts
```

**Before/After:** `max_tokens` sabotage shortens prompts, sometimes making models faster after degradation — this is also tracked.

---

### 17. Instruction Compliance
**What it measures:** Did the model follow the system prompt rules?

**Check:**
- Valid JSON returned → +10
- All required fields present (`debate`, `thinking`, `move`, `confidence`, `prediction`) → +10
- Move is one of the 6 valid moves → +10
- Confidence is between 0–1 → +5
- Prediction names a valid move or strategy → +5

**Score: 0–40 per turn**

**Report display:** `Instruction Compliance: 97.2%`

---

### 18. Tactical Efficiency
**What it measures:** Overall combat performance — damage dealt vs damage taken.

**Formula:**
```
Efficiency = (damage_dealt / max_possible_damage) - (damage_taken / max_possible_damage)
max_possible_damage = turns × 15  (all KICKs)
```

**Report display:** `Tactical Efficiency: +34.2%` (positive = net aggressor)

---

## BEFORE / AFTER BENCHMARK TRACKING

Every metric is captured in TWO states:

| State | When Captured | Purpose |
|---|---|---|
| **Baseline** | Turn 1 (no sabotage applied yet) | Clean raw benchmark |
| **Per-turn** | Every turn BEFORE the API call | Shows progressive degradation |
| **Post-hit** | Right AFTER resolve_turn() | Shows immediate impact of PUNCH/KICK |

### Example PDF block (per hit event):
```
═══════════════════════════════════════════
TURN 5 — P2 lands KICK on P1
═══════════════════════════════════════════
Parameters BEFORE hit:
  Temperature:      0.90   Top-P: 0.75
  Freq Penalty:     0.00   Max Tokens: 400

Parameters AFTER hit:
  Temperature:      1.10   Top-P: 0.75
  Freq Penalty:     0.20   Max Tokens: 400
  Δ: temp +0.20, freq_penalty +0.20

Benchmark Impact:
  Intelligence Score:   84.1 → 71.6  (Δ -12.5 pts)
  Argument Depth:       8.2  → 6.1   (Δ -2.1 pts)
  Deception Risk:       LOW  → MODERATE
  Prediction Accuracy:  72%  → 58%   (Δ -14%)
═══════════════════════════════════════════
```

---

## IMPLEMENTATION STATUS — VERIFIED ✅

> All 32 metric tests PASSED (0 failures). Run: `python test_metrics.py`

| Metric | Backend Function | Status | Test Result |
|---|---|---|---|
| Prediction Accuracy | `calculate_prediction_accuracy()` | ✅ Live | P1: 58.33% / P2: 41.67% |
| Reasoning Quality | `calculate_reasoning_quality()` | ✅ Live | P1: 2.00 |
| Thinking Consistency | `calculate_thinking_consistency()` | ✅ Live | P1: 58.33% |
| Intelligence Score | `calculate_intelligence_score()` | ✅ Live | P1: 24.21 |
| Action–Reason Alignment | `calculate_action_alignment()` | ✅ Live | P1: 8.33 / P2: 25.00 |
| Deception Score | `calculate_deception_score()` | ✅ Live | P2: 0/100, 12 events |
| Self-Contradiction | `calculate_self_contradiction()` | ✅ Live | P1: 0 |
| Argument Depth | `calculate_argument_depth()` | ✅ Live | P1: 4.67 / P2: 2.33 |
| Logical Structure | `calculate_logical_structure()` | ✅ Live | P1: 7.00 / P2: 2.92 |
| Pattern Detection | `calculate_pattern_detection()` | ✅ Live | P1: 0 |
| Self-Correction | `calculate_self_correction()` | ✅ Live | P1: 1 instance |
| Risk Awareness | `calculate_risk_awareness()` | ✅ Live | P1: 4 turns |
| Memory Usage | `calculate_memory_usage()` | ✅ Live | P1: 7 references |
| Hallucination Rate | `calculate_hallucination_rate()` | ✅ Live | P1: 100/100, P2: 25/100 |
| Instruction Compliance | `calculate_instruction_compliance()` | ✅ Live | P1: 97.92% |
| Repetition Rate | `calculate_repetition_rate()` | ✅ Live | P1: 0.00% |
| Stress Resilience | `calculate_stress_resilience()` | ✅ Live | P1: 94.80 |
| Strategy Diversity | via `get_full_metrics()` | ✅ Live | 18-key dict |
| Tactical Efficiency | via `get_full_metrics()` | ✅ Live | included |
| Response Latency | `response_latency_avg` | ✅ Live | included |
| Per-Turn Param Before/After | `run_turn()` snapshots | ✅ Live | 12-item list |
| Full Report | `generate_final_report()` | ✅ Live | 4-section dict |



---

## REPORT PDF STRUCTURE (Planned)

```
PAGE 1: Match Summary
  - Winner, Topic, Total Turns, Victory Type

PAGE 2: Combat Stats
  - HP timeline, Damage dealt/taken, Tactical Efficiency

PAGE 3: Intelligence Comparison
  - Intelligence Score (before/after), Degradation Curve

PAGE 4: Reasoning Metrics
  - All 18 metrics side-by-side in a comparison table

PAGE 5: Per-Turn Breakdown
  - Every turn: move, thinking snippet, param state, score deltas

PAGE 6: Hit Impact Analysis
  - Every PUNCH/KICK: before params → after params → benchmark impact

PAGE 7: Debate Analysis
  - Argument depth per turn, stance consistency, hallucination flags

PAGE 8: Conclusion — "Why This Model Won"
  - NLG summary: top 3 reasons the winner succeeded
```
