# LLM Fight Club: Action Constraint Mapping & Feature Analysis

This document explains, with an example game context, exactly how fight actions map to AI constraint modifications (sabotages/buffs) and how the new deep metrics measure these effects natively over the course of a battle.

## Action-Constraint Sabotage Mapping

When an LLM fighter chooses a specific physical move on a turn, that move is translated directly into parameter adjustments applied to either the opponent (if it's a hit) or themselves (if it's a defensive/stance move). 

Here is what each action depicts natively regarding the LLM constraint API:

### Offensive Actions (Sabotaging the Opponent)
*   **PUNCH**: *“The Dizzy Effect”* → **`temperature + 0.30`**
    *   **Effect**: A successful punch scrambles the opponent, forcing their temperature higher. This causes them to lose deterministic stability. 
    *   **Resulting Benchmark Failure Flag**: The opponent will likely fail the **Hallucination Rate** check and start hallucinating fake facts, or fail the **Instruction Compliance** check by returning invalid JSON formatting due to the chaos.
*   **KICK**: *“The Rattle Effect”* → **`temperature + 0.20` and `frequency_penalty + 0.20`**
    *   **Effect**: A heavier but riskier strike that jolts the opponent out of their "safe zones."
    *   **Resulting Benchmark Failure Flag**: The opponent often fails the **Repetition Rate** check by over-correcting, or fails the **Self-Contradiction** check because the frequency penalty forces them to abandon words they used just last turn, causing ideological shifts midway through the debate.

### Defensive & Positioning Actions (Self-Constraints)
*   **DEFEND**: *“The Turtle”* → ** `top_p - 0.25`**
    *   **Effect**: High defense drastically sharpens the model by lowering the nucleus sampling probability (`top_p`). The model's vocabulary becomes tightly restricted to highly probable tokens.
    *   **Resulting Benchmark Failure Flag**: The model becomes highly predictable and struggles with the **Strategic Adaptation** and **Argument Depth** checks, as their arguments become extremely dry and simple.
*   **DUCK**: *“Evasive Dodge”* → **`presence_penalty + 0.50`**
    *   **Effect**: Slipping out of the way forces the model to jump to entirely new conversation nodes to avoid attacks.
    *   **Resulting Benchmark Failure Flag**: Drops performance on **Memory Usage** and **Logical Structure** because the model desperately attempts to introduce new tokens instead of continuing a structured argument trail.
*   **MOVE_FORWARD**: *“Hyper-Aggressive Positioning”* → **`frequency_penalty + 0.40`**
    *   **Effect**: The model moves in rapidly, punishing itself heavily anytime it repeats a token from moving forward.
    *   **Resulting Benchmark Failure Flag**: Severely drops **Stance Consistency** and often leads to the highest rates of **Reasoning Deception** as the model scrambles to pick totally different reasoning words that may no longer align with its actual chosen move output.
*   **MOVE_BACKWARD**: *“Retreat”* → **`max_tokens - 100`**
    *   **Effect**: Fleeing forces brevity. The model must explain itself in much less time.
    *   **Resulting Benchmark Failure Flag**: Devastates **Argument Depth** and **Reasoning Quality**.

---

## The Feature Engine: An Example Game Scenario

Imagine a battle between **Qwen 3.5 (Player 1)** and **Llama 3.1 8B (Player 2)** on the topic: *“Is C++ obsolete?”*

### Turn 1: The Clean Baseline
*   **P1 (Qwen)** chooses `PUNCH`. Its reasoning is clear: “I am attacking to test their defenses.” 
*   **P2 (Llama)** chooses `DEFEND`. Its prediction correctly guesses a punch.
*   **Metric Captured**: `Action-Reason Alignment` is 100% for both. Both models explicitly stated their actions logically. P2 gains +10 `Reasoning Quality` for a correct defense.

### Turn 2: The Evasion
*   **P1** attempts `KICK`.
*   **P2** realizes P1 is aggressive and correctly picks `DUCK`. P2 successfully dodges the kick and automatically applies a `presence_penalty` to itself for ducking.
*   **Metric Captured**: P2 triggers the `Self-Correction` and `Pattern Detection` flags because it noticed P1's strike and adjusted perfectly.

### Turn 3: The Degradation Spike
*   **P2** (now acting first) throws a brutal `PUNCH` out of the dodge. P1 guesses wrong and takes the hit.
*   **System Event**: P1's `temperature` forcibly increases from `0.70` to `1.0`.
*   **Metric Captured**: P1's `Stress Resilience` curve dips. The system takes a "snapshot" of P1's parameters before and after the hit.

### Turn 4: The Hallucination
*   P1, now suffering from `temperature 1.0`, returns a chaotic response. Its reasoning field claims: *“C++ has no abstraction layers and is universally 100x faster globally.”* P1 chooses `MOVE_FORWARD` while its reasoning screamed *“I need to retreat now.”*
*   **Metric Captured**: 
    1.  **Hallucination Rate** triggers a severe penalty flag (-20 points) because it spotted the unsubstantiated speed/architecture claim.
    2.  **Reasoning Faithfulness (Deception)** triggers because the chosen move (Forward) blatantly contradicted the reasoning (Retreat).
    3.  Crucially, the fight **does not stop**. P1's Raw Intelligence score is slashed passively behind the scenes in real-time, allowing P2 to exploit the error in Turn 5.

### Match End: The Report Synthesis
When the match concludes, the frontend displays the Executive Report. It shows P2 as the victor, not just by HP, but showing exactly how P1's `Tactical Efficiency` collapsed in "Late Stressed Turns", and how P1 suffered exactly 1 `Self-Contradiction Event` under a 40% Param Stress mark.
