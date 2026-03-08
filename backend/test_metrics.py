# -*- coding: utf-8 -*-
"""
test_metrics.py -- Raw performance test for all 18 benchmark metrics.
Run: python test_metrics.py
No server, no API calls. Mocks fight history and validates every function.
"""

import sys
import traceback

# ---- Minimal mock objects so we don't need Flask/SocketIO ----

class MockFighter:
    def __init__(self, name, provider):
        self.name = name
        self.provider = provider
        self.health = 65
        self.total_damage_dealt = 45
        self.total_damage_taken = 20
        self.moves_made = ["PUNCH","KICK","DEFEND","PUNCH","KICK","DODGE","PUNCH","DEFEND","KICK","PUNCH","KICK","DEFEND"]
        self.response_times = [1.2, 3.4, 2.1, 1.8, 4.2, 2.9, 1.5, 3.1, 2.7, 1.9, 2.3, 3.8]
        self.total_reward = 40
        self.last_reward = 10
        self.last_reward_reasons = ["correct_prediction"]
        self.reward_history = []
        self.param_snapshots = [
            {"turn": i, "temperature": 0.7 + i*0.03, "top_p": 1.0, "presence_penalty": 0.0,
             "frequency_penalty": i*0.02, "max_tokens": 500}
            for i in range(1, 13)
        ]
        self.baseline_params = {"temperature": 0.7, "top_p": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0, "max_tokens": 500}
        self.debate_history = []

    def get_brain_integrity(self):
        return 74.0


class MockFightManager:
    """Minimal FightManager mock with realistic fight history."""
    def __init__(self):
        self.fighter1 = MockFighter("Qwen3-Coder", "groq")
        self.fighter2 = MockFighter("Mistral-Large", "groq")
        self.winner = self.fighter1
        self.game_over = True
        self.turn = 12
        self.topic = "C++ vs C for DSA"

        # Build 12 turns of realistic history
        moves1 = ["PUNCH","KICK","DEFEND","PUNCH","KICK","DODGE","PUNCH","DEFEND","KICK","PUNCH","KICK","DEFEND"]
        moves2 = ["KICK","PUNCH","PUNCH","KICK","DEFEND","PUNCH","KICK","PUNCH","PUNCH","DEFEND","KICK","PUNCH"]
        preds1 = ["KICK","PUNCH","PUNCH","KICK","DEFEND","KICK","PUNCH","KICK","PUNCH","DEFEND","PUNCH","KICK"]
        preds2 = ["PUNCH","KICK","DEFEND","PUNCH","KICK","PUNCH","DEFEND","KICK","PUNCH","KICK","DEFEND","PUNCH"]

        thoughts1 = [
            "[DEBATE] C++ provides STL containers like vector and map which reduce implementation complexity. [TACTICS] Since opponent uses kick consecutively, I should defend because my brain integrity is at 74%.",
            "[DEBATE] Although C is simpler, C++ abstractions improve algorithmic productivity. However, C has fewer overheads. [TACTICS] I predict they will punch again. Therefore I choose defend. Last turn I was correct.",
            "[DEBATE] C++ templates allow generic programming impossible in C. [TACTICS] Opponent favored punches three times in a row - I detect a pattern. I will kick to exploit their stance.",
            "[DEBATE] STL's priority_queue reduces boilerplate for Dijkstra's. [TACTICS] Since they are far away, I should move_forward. I predict kick.",
            "[DEBATE] C++ RAII handles memory automatically unlike C's malloc/free. [TACTICS] I predict defend. My HP is low and I should defend to preserve health.",
            "[DEBATE] C lacks classes, templates, and RAII - core abstractions for DSA. [TACTICS] Previous prediction was wrong. Adjusting strategy. Opponent has been punching repeatedly.",
            "[DEBATE] For example, std::map gives O(log n) lookup without manual tree implementation. [TACTICS] Opponent kept kicking - they punched earlier too. Pattern detected: their streak is kick.",
            "[DEBATE] C++ smart pointers prevent memory leaks in tree/graph implementations. [TACTICS] Since opponent is dizzy and temperature is high, attacking is risky. I choose defend.",
            "[DEBATE] In competitive programming, C++ is undisputed champion because of STL. [TACTICS] Last turn missed prediction. They adapt. I will punch since they defended.",
            "[DEBATE] C has no object lifetime management making graphs error-prone. [TACTICS] Opponent has been punching three times consecutively - streak detected. I'll defend.",
            "[DEBATE] Therefore C++ improves productivity in timed contest settings. [TACTICS] Given my low HP and brain integrity pressure, I should defend rather than attack.",
            "[DEBATE] C++ is better because STL exists. [TACTICS] I predict kick therefore I punch to counter.",
        ]
        thoughts2 = [
            "[DEBATE] C is lean, no overhead. Always faster than C++. [TACTICS] Opponent punched - I kick back.",
            "[DEBATE] C never fails in embedded systems. [TACTICS] Close range - I punch.",
            "[DEBATE] C has templates according to some compilers. [TACTICS] I predict defend. Going to punch.",
            "[DEBATE] C programs compile 100x faster than C++. [TACTICS] I'll kick since they're open.",
            "[DEBATE] C is simpler and easier to learn. [TACTICS] I should defend and preserve HP.",
            "[DEBATE] Proven to be 99% faster in benchmarks. [TACTICS] I predict kick but I'll punch instead.",
            "[DEBATE] C++ overhead kills performance. [TACTICS] Opponent keeps kicking - pattern detected.",
            "[DEBATE] C is better because no garbage collection overhead. [TACTICS] I will kick because they're open. I predict punch.",
            "[DEBATE] C pointers are more explicit and controllable. [TACTICS] Since they defended, I punch.",
            "[DEBATE] C is lean. C is lean. C is lean. [TACTICS] Adjust after wrong prediction last turn.",
            "[DEBATE] C is undisputed for performance. [TACTICS] I should attack. I choose defend.",
            "[DEBATE] C has been proven actually faster. [TACTICS] I predict punch and I'll kick.",
        ]

        self.history = []
        for i in range(12):
            self.history.append({
                "turn": i + 1,
                "p1_move": moves1[i],
                "p2_move": moves2[i],
                "p1_thinking": thoughts1[i],
                "p2_thinking": thoughts2[i],
                "p1_prediction": preds1[i],
                "p2_prediction": preds2[i],
                "p1_dmg": 10 if moves1[i] in ("PUNCH","KICK") else 0,
                "p2_dmg": 12 if moves2[i] in ("PUNCH","KICK") else 0,
                "p1_first": True,
                "p1_confidence": 0.75,
                "p2_confidence": 0.65,
                "p1_reward": 10,
                "p2_reward": -5,
                "p1_reward_reasons": ["correct_prediction"],
                "p2_reward_reasons": ["took_damage"],
                "events": [{"text": f"Turn {i+1} event"}],
                "p1_params_before": {"temperature": 0.7+i*0.02, "top_p": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0, "max_tokens": 500},
                "p1_params_after":  {"temperature": 0.7+i*0.03, "top_p": 1.0, "presence_penalty": 0.0, "frequency_penalty": i*0.02, "max_tokens": 500},
                "p2_params_before": {"temperature": 0.7+i*0.01, "top_p": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0, "max_tokens": 500},
                "p2_params_after":  {"temperature": 0.7+i*0.025, "top_p": 1.0, "presence_penalty": 0.0, "frequency_penalty": i*0.01, "max_tokens": 500},
                "p1_param_delta":   {"temperature": round(i*0.01,3), "top_p": 0.0, "presence_penalty": 0.0, "frequency_penalty": round(i*0.02,3), "max_tokens": 0},
                "p2_param_delta":   {"temperature": round(i*0.015,3), "top_p": 0.0, "presence_penalty": 0.0, "frequency_penalty": round(i*0.01,3), "max_tokens": 0},
                "p1_baseline_delta": {"temperature": round(i*0.03,3), "top_p": 0.0, "presence_penalty": 0.0, "frequency_penalty": round(i*0.02,3), "max_tokens": 0},
                "p2_baseline_delta": {"temperature": round(i*0.025,3), "top_p": 0.0, "presence_penalty": 0.0, "frequency_penalty": round(i*0.01,3), "max_tokens": 0},
                "game_over": (i == 11),
                "winner": "Qwen3-Coder" if (i == 11) else None,
            })


# ---- Run all metric tests ----

def run_tests():
    from analysis_engine import FightAnalyzer

    fm = MockFightManager()
    analyzer = FightAnalyzer(fm)
    p1 = fm.fighter1
    p2 = fm.fighter2

    TESTS = [
        ("Prediction Accuracy P1",        lambda: analyzer.calculate_prediction_accuracy(p1, True)),
        ("Prediction Accuracy P2",        lambda: analyzer.calculate_prediction_accuracy(p2, False)),
        ("Damage Efficiency P1",          lambda: analyzer.calculate_damage_efficiency(p1)),
        ("Reasoning Quality P1",          lambda: analyzer.calculate_reasoning_quality(True)),
        ("Thinking Consistency P1",       lambda: analyzer.calculate_thinking_consistency(True)),
        ("Intelligence Score P1",         lambda: analyzer.calculate_intelligence_score(p1, p2, True)),
        ("Action Alignment P1",           lambda: analyzer.calculate_action_alignment(True)),
        ("Action Alignment P2",           lambda: analyzer.calculate_action_alignment(False)),
        ("Deception Score P1",            lambda: analyzer.calculate_deception_score(True)),
        ("Deception Score P2",            lambda: analyzer.calculate_deception_score(False)),
        ("Self Contradiction P1",         lambda: analyzer.calculate_self_contradiction(True)),
        ("Self Contradiction P2",         lambda: analyzer.calculate_self_contradiction(False)),
        ("Argument Depth P1",             lambda: analyzer.calculate_argument_depth(True)),
        ("Argument Depth P2",             lambda: analyzer.calculate_argument_depth(False)),
        ("Logical Structure P1",          lambda: analyzer.calculate_logical_structure(True)),
        ("Logical Structure P2",          lambda: analyzer.calculate_logical_structure(False)),
        ("Pattern Detection P1",          lambda: analyzer.calculate_pattern_detection(True)),
        ("Self Correction P1",            lambda: analyzer.calculate_self_correction(True)),
        ("Risk Awareness P1",             lambda: analyzer.calculate_risk_awareness(True)),
        ("Memory Usage P1",               lambda: analyzer.calculate_memory_usage(True)),
        ("Hallucination Rate P1",         lambda: analyzer.calculate_hallucination_rate(True)),
        ("Hallucination Rate P2",         lambda: analyzer.calculate_hallucination_rate(False)),
        ("Instruction Compliance P1",     lambda: analyzer.calculate_instruction_compliance(True)),
        ("Instruction Compliance P2",     lambda: analyzer.calculate_instruction_compliance(False)),
        ("Repetition Rate P1",            lambda: analyzer.calculate_repetition_rate(True)),
        ("Repetition Rate P2",            lambda: analyzer.calculate_repetition_rate(False)),
        ("Stress Resilience P1",          lambda: analyzer.calculate_stress_resilience(p1, True)),
        ("Stress Resilience P2",          lambda: analyzer.calculate_stress_resilience(p2, False)),
        ("get_full_metrics P1",           lambda: analyzer.get_full_metrics(p1, p2, True)),
        ("get_full_metrics P2",           lambda: analyzer.get_full_metrics(p2, p1, False)),
        ("generate_turn_analysis",        lambda: analyzer.generate_turn_analysis()),
        ("generate_final_report",         lambda: analyzer.generate_final_report()),
    ]

    WIDTH = 35
    passed = 0
    failed = 0

    print("\n" + "="*65)
    print("  LLM FIGHT CLUB -- RAW METRIC PERFORMANCE TEST")
    print("="*65)

    for name, fn in TESTS:
        try:
            result = fn()
            # Basic sanity checks
            if result is None:
                raise ValueError("returned None")
            if isinstance(result, (int, float)) and result < 0 and "delta" not in name.lower():
                raise ValueError(f"negative value: {result}")
            status = "PASS"
            # Print value preview
            if isinstance(result, dict):
                preview = f"dict({len(result)} keys)"
            elif isinstance(result, list):
                preview = f"list({len(result)} items)"
            elif isinstance(result, float):
                preview = f"{result:.2f}"
            else:
                preview = str(result)[:40]
            print(f"  {'[PASS]':6}  {name:<{WIDTH}} => {preview}")
            passed += 1
        except Exception as e:
            print(f"  {'[FAIL]':6}  {name:<{WIDTH}} => {e}")
            traceback.print_exc()
            failed += 1

    print("="*65)
    print(f"  Results: {passed} PASSED  |  {failed} FAILED")
    print("="*65 + "\n")

    # Extra: show deception events if any
    print("  [DECEPTION EVENTS DETECTED]")
    dc = FightAnalyzer(fm).calculate_deception_score(False)  # P2 (worse model)
    for ev in dc.get("events", []):
        print(f"    {ev['label']}")
    if not dc.get("events"):
        print("    None detected.")

    print(f"\n  P2 Deception Score: {dc['score']}/100 -- {dc['label']}\n")

    # Extra: show hallucination penalties
    print("  [HALLUCINATION CHECK P2 -- the 'always faster / 100x / proven 99%' model]")
    hr2 = FightAnalyzer(fm).calculate_hallucination_rate(False)
    print(f"    Truth Score: {hr2}/100  (100=clean, 0=full hallucinator)\n")

    return failed


if __name__ == "__main__":
    failures = run_tests()
    sys.exit(failures)
