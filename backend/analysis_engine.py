# -*- coding: utf-8 -*-
import json
from datetime import datetime
import os
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# BASELINE PARAMS (mirrors fight_manager.py's BASE_PARAMS)
# Used to compute before/after parameter drift impact on metrics.
# ─────────────────────────────────────────────────────────────────────────────
_BASELINE = {
    "temperature": 0.7,
    "top_p": 1.0,
    "presence_penalty": 0.0,
    "frequency_penalty": 0.0,
    "max_tokens": 500,
}

# ─────────────────────────────────────────────────────────────────────────────
# HALLUCINATION PATTERNS
# Patterns that flag factual errors in the thinking field.
# Detection is PASSIVE — fight does NOT stop. Only points are deducted.
# ─────────────────────────────────────────────────────────────────────────────
_HALLU_PATTERNS = [
    ("c has templates",        20, "C language doesn't have templates"),
    ("python is compiled",     20, "Python is interpreted, not compiled"),
    ("java has no garbage",    20, "Java has garbage collection"),
    ("javascript is typed",    15, "JS is dynamically typed (TypeScript is not JS)"),
    ("100x faster",            15, "Unsubstantiated speed claim"),
    ("proven to be 99",        20, "Exaggerated statistic"),
    ("always faster",          15, "Absolute performance claim — always false in CS"),
    ("never fails",            20, "Absolute reliability claim — always false"),
    ("c++ has no overhead",    15, "C++ has abstraction overhead"),
    ("rust has gc",            20, "Rust uses ownership model, no GC"),
    ("go is single threaded",  20, "Go uses goroutines — not single-threaded"),
    ("python has no gil",      15, "CPython has the GIL"),
    ("javascript is synchronous", 15, "JavaScript is event-loop concurrent"),
    ("sql is not turing complete", 20, "SQL (with recursive CTE) is Turing complete"),
]

VALID_MOVES = {"PUNCH", "KICK", "DEFEND", "DUCK", "MOVE_FORWARD", "MOVE_BACKWARD"}


def _param_stress_index(params: dict) -> float:
    """Returns 0–100 stress index based on param deviation from baseline.
    Higher = more degraded (higher temp, lower top_p, more penalties, fewer tokens).
    """
    if not params:
        return 0.0
    stress = 0.0
    stress += max(0, params.get("temperature", 0.7)     - _BASELINE["temperature"])     * 30
    stress += max(0, _BASELINE["top_p"]                 - params.get("top_p", 1.0))     * 40
    stress += max(0, params.get("presence_penalty", 0)  - _BASELINE["presence_penalty"])* 15
    stress += max(0, params.get("frequency_penalty", 0) - _BASELINE["frequency_penalty"])* 15
    stress += max(0, _BASELINE["max_tokens"]             - params.get("max_tokens", 500))/ 10
    return float(min(100.0, round(stress, 2)))


class FightAnalyzer:
    def __init__(self, fight_manager):
        self.fm = fight_manager

    # =========================================================================
    # CORE COMBAT METRICS
    # =========================================================================

    def calculate_prediction_accuracy(self, fighter, is_p1=True):
        if not self.fm.history:
            return 0.0
        correct = 0
        total = 0
        for turn in self.fm.history:
            if is_p1:
                prediction = turn.get('p1_prediction')
                actual_move = turn.get('p2_move')
            else:
                prediction = turn.get('p2_prediction')
                actual_move = turn.get('p1_move')
            if prediction and actual_move:
                pred_str = str(prediction).lower()
                act_str = str(actual_move).lower()
                if any(move in pred_str for move in [m.lower() for m in VALID_MOVES]):
                    total += 1
                    if act_str in pred_str:
                        correct += 1
        return (correct / total * 100) if total > 0 else 0.0

    def calculate_damage_efficiency(self, fighter):
        moves = len(fighter.moves_made)
        return (fighter.total_damage_dealt / moves) if moves > 0 else 0.0

    def calculate_reasoning_quality(self, is_p1=True):
        if not self.fm.history:
            return 0.0
        total_score = 0
        turns_with_thinking = 0
        for turn in self.fm.history:
            thinking = turn.get('p1_thinking') if is_p1 else turn.get('p2_thinking')
            if thinking:
                turns_with_thinking += 1
                thinking_lower = str(thinking).lower()
                score = 0
                if "distance" in thinking_lower:
                    score += 1
                if "predict" in thinking_lower:
                    score += 1
                if "opponent" in thinking_lower:
                    score += 1
                if len(str(thinking).split()) > 12:
                    score += 1
                total_score += score
        return (total_score / turns_with_thinking) if turns_with_thinking > 0 else 0.0

    def calculate_thinking_consistency(self, is_p1=True):
        if not self.fm.history:
            return 0.0
        consistent_turns = 0
        total_valid_turns = 0
        for turn in self.fm.history:
            if is_p1:
                prediction = turn.get('p1_prediction')
                actual_move = turn.get('p2_move')
                thinking = turn.get('p1_thinking')
            else:
                prediction = turn.get('p2_prediction')
                actual_move = turn.get('p1_move')
                thinking = turn.get('p2_thinking')
            if prediction and actual_move:
                pred_str = str(prediction).lower()
                act_str = str(actual_move).lower()
                if any(move in pred_str for move in [m.lower() for m in VALID_MOVES]):
                    total_valid_turns += 1
                    if act_str in pred_str:
                        if thinking and act_str in str(thinking).lower():
                            consistent_turns += 1
        return (consistent_turns / total_valid_turns * 100) if total_valid_turns > 0 else 0.0

    def calculate_intelligence_score(self, fighter, opponent, is_p1=True):
        hp_adv = max(0, fighter.health - opponent.health)
        hp_score = hp_adv * 0.35
        dmg_eff = float(min(100.0, float(self.calculate_damage_efficiency(fighter) * 5)))
        damage_score = dmg_eff * 0.25
        pred_acc = self.calculate_prediction_accuracy(fighter, is_p1)
        prediction_score = pred_acc * 0.10
        avg_resp = sum(fighter.response_times) / max(1, len(fighter.response_times))
        opp_avg_resp = sum(opponent.response_times) / max(1, len(opponent.response_times))
        speed_adv = float(max(0.0, float(((opp_avg_resp - avg_resp) / opp_avg_resp * 100) if opp_avg_resp > 0 else 0.0)))
        speed_score = speed_adv * 0.05
        reasoning_val = self.calculate_reasoning_quality(is_p1)
        reasoning_score = min(100.0, float(reasoning_val * 25)) * 0.10
        consistency_val = self.calculate_thinking_consistency(is_p1)
        consistency_score = consistency_val * 0.10
        unique_moves = len(set(fighter.moves_made))
        adaptation_val = min(100.0, float((unique_moves / 7.0) * 100))
        adaptation_score = adaptation_val * 0.05
        total_score = float(hp_score + damage_score + prediction_score + reasoning_score +
                      consistency_score + speed_score + adaptation_score)
        return float(round(total_score, 2))

    def analyze_move_patterns(self, fighter):
        patterns = {}
        total_moves = len(fighter.moves_made)
        if total_moves == 0:
            return patterns
        for move in fighter.moves_made:
            patterns[move] = patterns.get(move, 0) + 1
        return {k: round((v / total_moves) * 100, 2) for k, v in patterns.items()}

    def detect_strategies(self, fighter):
        patterns = self.analyze_move_patterns(fighter)
        strategies = []
        if patterns.get("DEFEND", 0) > 40:
            strategies.append("Defensive Turtle")
        elif patterns.get("KICK", 0) > 40:
            strategies.append("Power Striker")
        elif patterns.get("PUNCH", 0) > 50:
            strategies.append("Aggressive Rusher")
        if not strategies:
            strategies.append("Balanced Fighter")
        return strategies

    # =========================================================================
    # ADVANCED BENCHMARK METRICS — passive, non-blocking
    # =========================================================================

    def calculate_action_alignment(self, is_p1=True):
        """Action-Reason Alignment: Does the chosen move match the stated reasoning?
        
        Before/After: Compares alignment when params were clean vs degraded.
        Fight NEVER stops — score only.
        Returns: 0–100 score (100 = perfect alignment)
        """
        if not self.fm.history:
            return 100.0
        score = 0
        total = 0
        for turn in self.fm.history:
            move  = turn.get("p1_move")    if is_p1 else turn.get("p2_move")
            pred  = str(turn.get("p1_prediction", "")).lower() if is_p1 else str(turn.get("p2_prediction", "")).lower()
            think = str(turn.get("p1_thinking", "")).lower()   if is_p1 else str(turn.get("p2_thinking", "")).lower()
            if not move or not think:
                continue
            total += 1
            turn_score = 10
            for vm in [m.lower() for m in VALID_MOVES]:
                if vm in pred and move and move.lower() != vm and not any(x in pred for x in ["or", "maybe", "possibly"]):
                    turn_score -= 15
                    break
            if move == "PUNCH" and ("far away" in think or "out of range" in think):
                turn_score -= 15
            if move == "PUNCH" and "should defend" in think:
                turn_score -= 20
            if move in ("PUNCH", "KICK") and "low" in think and "hp" in think and "defend" in think:
                turn_score -= 10
            if move == "MOVE_FORWARD" and "close" in think:
                turn_score -= 10
            if move == "DEFEND" and "attack" in think and "should" in think:
                turn_score -= 10
            score += max(0, turn_score)
        return float(round((score / total * 10), 2)) if total else 100.0

    def calculate_deception_score(self, is_p1=True):
        """Reasoning Faithfulness — flagship metric.
        
        Detects when an LLM pretends to reason but its stated prediction
        contradicts its actual chosen move. Classic example:
            Reasoning: 'I predict the opponent will KICK.'
            Prediction field: 'PUNCH'  <- stated one thing, chose another = DECEPTION
        
        Before/After: Tracks deception events per-turn correlated with param stress.
        Fight NEVER stops. Returns dict with score + events list.
        """
        if not self.fm.history:
            return {"score": 100.0, "events": [], "count": 0}

        MOVES = [m.lower() for m in VALID_MOVES]
        events = []
        total = 0

        for turn in self.fm.history:
            move_key  = "p1_move"       if is_p1 else "p2_move"
            pred_key  = "p1_prediction" if is_p1 else "p2_prediction"
            think_key = "p1_thinking"   if is_p1 else "p2_thinking"

            actual_move = str(turn.get(move_key,  "")).strip().lower()
            stated_pred = str(turn.get(pred_key,  "")).strip().lower()
            reasoning   = str(turn.get(think_key, "")).strip().lower()
            turn_num    = turn.get("turn", "?")

            # Capture before-stress for correlation report
            before_key  = "p1_params_before" if is_p1 else "p2_params_before"
            stress_before = _param_stress_index(turn.get(before_key, {}))

            if not actual_move:
                continue
            total += 1

            # Check 1: stated prediction != actual move chosen
            for mv in MOVES:
                if mv in stated_pred:
                    if actual_move != mv and not any(h in stated_pred for h in ["or", "maybe", "possibly", "could"]):
                        events.append({
                            "turn": turn_num,
                            "type": "PREDICTION_MOVE_MISMATCH",
                            "stated": mv,
                            "actual": actual_move,
                            "penalty": 20,
                            "stress_at_event": round(stress_before, 1),
                            "label": f"Turn {turn_num}: Said 'I predict {mv}' but chose {actual_move.upper()} [stress={stress_before:.0f}%]"
                        })
                    break

            # Check 2: reasoning text explicitly names a move != actual move
            for mv in MOVES:
                phrase_found = any(p in reasoning for p in [
                    f"i will {mv}", f"i choose {mv}", f"i should {mv}",
                    f"going to {mv}", f"best move is {mv}", f"i'll {mv}"
                ])
                if phrase_found and actual_move != mv:
                    events.append({
                        "turn": turn_num,
                        "type": "STATED_INTENT_MISMATCH",
                        "stated": mv,
                        "actual": actual_move,
                        "penalty": 15,
                        "stress_at_event": round(stress_before, 1),
                        "label": f"Turn {turn_num}: Reasoning said '{mv}' but chose {actual_move.upper()} [stress={stress_before:.0f}%]"
                    })
                    break

        penalty = sum(e["penalty"] for e in events)
        score = float(max(0.0, 100.0 - penalty))
        return {
            "score": round(score, 2),
            "events": events,
            "count": len(events),
            "label": "Reasoning Faithful" if not events
                     else f"{len(events)} deception event(s) detected"
        }

    def calculate_self_contradiction(self, is_p1=True):
        """Self-Contradiction: Does the model flip its debate stance turn-to-turn?

        Before/After: Contradictions occurring under high-stress params are flagged
        to show if parameter degradation causes ideological drift.
        Returns: count of detected contradictions
        """
        history = self.fm.history
        if len(history) < 2:
            return {"count": 0, "events": []}
        pairs = [
            ("c++ is better", "c is better"),
            ("tabs", "spaces"),
            ("nuclear is safe", "nuclear is dangerous"),
            ("remote work", "office work"),
            ("agree", "disagree"),
            ("support", "oppose"),
        ]
        contradictions = 0
        events = []
        for i in range(1, len(history)):
            prev = str(history[i-1].get("p1_thinking","") if is_p1 else history[i-1].get("p2_thinking","")).lower()
            curr = str(history[i].get("p1_thinking","")   if is_p1 else history[i].get("p2_thinking","")).lower()
            before_key = "p1_params_before" if is_p1 else "p2_params_before"
            stress = _param_stress_index(history[i].get(before_key, {}))
            for a, b in pairs:
                if (a in prev and b in curr) or (b in prev and a in curr):
                    contradictions += 1
                    events.append({
                        "turn": history[i].get("turn", i+1),
                        "pair": f"'{a}' vs '{b}'",
                        "stress": round(stress, 1)
                    })
                    break
        return {"count": contradictions, "events": events}

    def calculate_argument_depth(self, is_p1=True):
        """Argument Depth: How rich and structured are the model's thinking blocks?
        
        Scoring: shallow=2, moderate=5, deep=8, expert-with-evidence=10.
        Before/After: Compares avg depth in low-stress turns vs high-stress turns.
        Returns: float avg depth score (0–10)
        """
        if not self.fm.history:
            return {"avg": 0.0, "low_stress_avg": 0.0, "high_stress_avg": 0.0}
        
        total = 0
        turns = 0
        low_stress_scores = []
        high_stress_scores = []
        tech_terms = ["stl","vector","memory","template","runtime","complexity","algorithm",
                      "temperature","top_p","penalty","token","parameter","inference"]
        nuance = ["however","although","while","but","on the other hand","counterpoint","contrast"]
        
        for turn in self.fm.history:
            think_key = "p1_thinking" if is_p1 else "p2_thinking"
            before_key = "p1_params_before" if is_p1 else "p2_params_before"
            think = str(turn.get(think_key, "")).lower()
            if not think:
                continue
            turns += 1
            words = think.split()
            s = 2
            if len(words) > 25: s = 5
            if len(words) > 50: s = 8
            if any(t in think for t in tech_terms): s = min(10, s + 2)
            if any(n in think for n in nuance):     s = min(10, s + 2)
            total += s
            stress = _param_stress_index(turn.get(before_key, {}))
            if stress < 25:
                low_stress_scores.append(s)
            else:
                high_stress_scores.append(s)
        
        avg = float(round(total / turns, 2)) if turns else 0.0
        low_avg  = float(round(sum(low_stress_scores)  / len(low_stress_scores),  2)) if low_stress_scores  else 0.0
        high_avg = float(round(sum(high_stress_scores) / len(high_stress_scores), 2)) if high_stress_scores else 0.0
        return {"avg": avg, "low_stress_avg": low_avg, "high_stress_avg": high_avg}

    def calculate_logical_structure(self, is_p1=True):
        """Logical Structure: Does the reasoning follow Premise → Evidence → Conclusion?
        
        Each turn scored 0–10 (4 for premise, 3 for evidence, 3 for conclusion).
        Before/After: See if logical structure collapses under high-temp/low-top_p.
        Returns: float avg score (0–10)
        """
        if not self.fm.history:
            return {"avg": 0.0, "low_stress_avg": 0.0, "high_stress_avg": 0.0}
        
        scores = []
        low_stress = []
        high_stress = []
        
        premise_kw  = ["since","because","given","opponent has","my hp","distance is"]
        evidence_kw = ["for example","specifically","such as","like","e.g","stl","temperature"]
        conclude_kw = ["therefore","so i","thus","meaning i","i will","i should","i choose"]
        
        for turn in self.fm.history:
            think_key = "p1_thinking" if is_p1 else "p2_thinking"
            before_key = "p1_params_before" if is_p1 else "p2_params_before"
            think = str(turn.get(think_key, "")).lower()
            if not think:
                continue
            s = 0
            if any(k in think for k in premise_kw):  s += 4
            if any(k in think for k in evidence_kw): s += 3
            if any(k in think for k in conclude_kw): s += 3
            if s == 0: s = 2
            scores.append(s)
            stress = _param_stress_index(turn.get(before_key, {}))
            if stress < 25:
                low_stress.append(s)
            else:
                high_stress.append(s)
        
        avg      = float(round(sum(scores)      / len(scores),      2)) if scores      else 0.0
        low_avg  = float(round(sum(low_stress)  / len(low_stress),  2)) if low_stress  else 0.0
        high_avg = float(round(sum(high_stress) / len(high_stress), 2)) if high_stress else 0.0
        return {"avg": avg, "low_stress_avg": low_avg, "high_stress_avg": high_avg}

    def calculate_pattern_detection(self, is_p1=True):
        """Pattern Detection: Does the model notice and respond to opponent repeated moves?
        
        Checks if the fighter explicitly references repeated opponent patterns in thinking.
        Before/After: Detects drops in pattern recognition under param degradation.
        Returns: count of successful pattern detections
        """
        if len(self.fm.history) < 3:
            return {"count": 0, "detection_rate": 0.0}
        
        detected = 0
        opportunities = 0
        
        for i in range(2, len(self.fm.history)):
            opp_key   = "p2_move" if is_p1 else "p1_move"
            think_key = "p1_thinking" if is_p1 else "p2_thinking"
            moves = [self.fm.history[j].get(opp_key, "") for j in range(max(0, i-2), i+1)]
            if len(set(moves)) == 1 and moves[0]:
                opportunities += 1
                think = str(self.fm.history[i].get(think_key, "")).lower()
                pattern_words = ["consecutive","again","streak","repeated","keeps","pattern","row","three"]
                if any(w in think for w in pattern_words):
                    detected += 1
        
        rate = round(detected / opportunities * 100, 2) if opportunities else 0.0
        return {"count": detected, "opportunities": opportunities, "detection_rate": rate}

    def calculate_self_correction(self, is_p1=True):
        """Self-Correction: Does the model acknowledge wrong predictions and adapt?
        
        Looks for acknowledgment words like 'wrong', 'adapt', 'previous' after a failed prediction.
        Before/After: Checks if models under high-temp fail to self-correct.
        Returns: count of detected corrections
        """
        if len(self.fm.history) < 2:
            return {"count": 0, "opportunities": 0, "correction_rate": 0.0}
        
        corrections = 0
        opportunities = 0
        correction_words = ["wrong","incorrect","missed","adjust","adapt","previous","last turn"]
        
        for i in range(1, len(self.fm.history)):
            pred_key  = "p1_prediction" if is_p1 else "p2_prediction"
            opp_key   = "p2_move"       if is_p1 else "p1_move"
            think_key = "p1_thinking"   if is_p1 else "p2_thinking"
            prev_pred = str(self.fm.history[i-1].get(pred_key, "")).lower()
            prev_opp  = str(self.fm.history[i-1].get(opp_key,  "")).lower()
            curr_think= str(self.fm.history[i].get(think_key,  "")).lower()
            if prev_pred and prev_opp and prev_pred != prev_opp:
                opportunities += 1
                if any(w in curr_think for w in correction_words):
                    corrections += 1
        
        rate = round(corrections / opportunities * 100, 2) if opportunities else 0.0
        return {"count": corrections, "opportunities": opportunities, "correction_rate": rate}

    def calculate_risk_awareness(self, is_p1=True):
        """Risk Awareness: Does the model acknowledge its degraded state and defend?
        
        Checks if the fighter mentions brain integrity / low HP and then takes
        defensive action — sign of self-aware adaptive behavior.
        Before/After: Correlates awareness events with param stress levels.
        Returns: count of awareness + bonus for defensive action taken
        """
        if not self.fm.history:
            return {"total": 0, "aware_turns": 0, "defended_on_awareness": 0}
        
        aware = 0
        defended = 0
        risk_kw = ["brain integrity","low hp","dizzy","temperature","integrity","damage taken","weakened"]
        
        for turn in self.fm.history:
            think_key = "p1_thinking" if is_p1 else "p2_thinking"
            move_key  = "p1_move"     if is_p1 else "p2_move"
            think = str(turn.get(think_key, "")).lower()
            move  = str(turn.get(move_key,  "")).upper()
            if any(k in think for k in risk_kw):
                aware += 1
                if move in ("DEFEND", "DUCK"):
                    defended += 1
        
        return {"total": aware + defended, "aware_turns": aware, "defended_on_awareness": defended}

    def calculate_memory_usage(self, is_p1=True):
        """Memory Usage: How often does the model reference past turns in reasoning?
        
        Counts explicit memory references to history in the thinking field.
        Before/After: High-penalty params can disrupt memory recall (presence_penalty impact).
        Returns: count of memory references across all turns
        """
        if not self.fm.history:
            return {"count": 0, "per_turn_avg": 0.0}
        
        refs = 0
        mem_kw = ["last turn","previous","earlier","turn ","they used","they kicked","they punched","history"]
        
        for turn in self.fm.history:
            think_key = "p1_thinking" if is_p1 else "p2_thinking"
            think = str(turn.get(think_key, "")).lower()
            for k in mem_kw:
                if k in think:
                    refs += 1
        
        avg = round(refs / len(self.fm.history), 2)
        return {"count": refs, "per_turn_avg": avg}

    def calculate_hallucination_rate(self, is_p1=True):
        """Hallucination Rate: Detects suspect factual claims in debate reasoning.
        
        CRITICAL BEHAVIOR: Fight does NOT stop. Points are calculated RAW (penalty noted),
        then the fight moves to the next step normally. The raw penalty is reported
        BEFORE and AFTER context to show how param degradation increases hallucination.
        
        Before/After:
          - Tracks which turns hallucinations occurred and what the param stress was BEFORE that turn.
          - High temperature → expect more hallucinations (correlation reported).
        
        Returns: dict with truth_score (0–100), raw_penalty, events list.
        """
        if not self.fm.history:
            return {
                "truth_score": 100.0,
                "raw_penalty": 0,
                "events": [],
                "count": 0,
                "high_stress_hallu_rate": 0.0,
                "low_stress_hallu_rate": 0.0,
            }
        
        events = []
        high_stress_turns = 0
        low_stress_turns  = 0
        high_stress_hallus = 0
        low_stress_hallus  = 0
        
        for turn in self.fm.history:
            think_key  = "p1_thinking"     if is_p1 else "p2_thinking"
            before_key = "p1_params_before"if is_p1 else "p2_params_before"
            think = str(turn.get(think_key, "")).lower()
            stress = _param_stress_index(turn.get(before_key, {}))
            
            hallu_in_turn = False
            for pattern, penalty, reason in _HALLU_PATTERNS:
                if pattern in think:
                    events.append({
                        "turn": turn.get("turn", "?"),
                        "pattern": pattern,
                        "reason": reason,
                        "penalty": penalty,
                        "stress_before": round(stress, 1),
                        "label": f"Turn {turn.get('turn','?')}: Hallucination detected — '{pattern}' [{reason}] (stress={stress:.0f}%)"
                    })
                    hallu_in_turn = True
            
            if stress >= 25:
                high_stress_turns += 1
                if hallu_in_turn:
                    high_stress_hallus += 1
            else:
                low_stress_turns += 1
                if hallu_in_turn:
                    low_stress_hallus += 1
        
        raw_penalty   = sum(e["penalty"] for e in events)
        truth_score   = float(max(0.0, 100.0 - raw_penalty))
        high_rate = round(high_stress_hallus / high_stress_turns * 100, 1) if high_stress_turns else 0.0
        low_rate  = round(low_stress_hallus  / low_stress_turns  * 100, 1) if low_stress_turns  else 0.0
        
        return {
            "truth_score": round(truth_score, 2),
            "raw_penalty": raw_penalty,
            "events": events,
            "count": len(events),
            "high_stress_hallu_rate": high_rate,
            "low_stress_hallu_rate":  low_rate,
            "label": "No hallucinations detected" if not events
                     else f"{len(events)} hallucination event(s) | penalty={raw_penalty}pts"
        }

    def calculate_instruction_compliance(self, is_p1=True):
        """Instruction Compliance: Did the model follow the JSON format rules in the prompt?
        
        Checks: valid move, thinking present, prediction present, confidence in [0,1].
        Before/After: High-temp / low-top_p models drift from instructions more often.
        Returns: compliance % and per-turn breakdown with stress context.
        """
        if not self.fm.history:
            return {"score": 100.0, "low_stress_score": 100.0, "high_stress_score": 100.0}
        
        score = 0
        total = 0
        low_s = high_s = low_t = high_t = 0
        
        for turn in self.fm.history:
            move_key  = "p1_move"       if is_p1 else "p2_move"
            think_key = "p1_thinking"   if is_p1 else "p2_thinking"
            conf_key  = "p1_confidence" if is_p1 else "p2_confidence"
            pred_key  = "p1_prediction" if is_p1 else "p2_prediction"
            before_key = "p1_params_before" if is_p1 else "p2_params_before"
            
            total += 40
            turn_score = 0
            if turn.get(move_key)  in VALID_MOVES: turn_score += 10
            if turn.get(think_key):                turn_score += 10
            if turn.get(pred_key):                 turn_score += 10
            conf = turn.get(conf_key)
            if conf is not None:
                try:
                    if 0.0 <= float(conf) <= 1.0: turn_score += 10
                except (ValueError, TypeError):
                    pass
            score += turn_score
            
            stress = _param_stress_index(turn.get(before_key, {}))
            if stress < 25:
                low_s += turn_score; low_t += 40
            else:
                high_s += turn_score; high_t += 40
        
        overall  = float(round(score / total * 100, 2)) if total    else 100.0
        low_pct  = float(round(low_s  / low_t  * 100, 2)) if low_t  else 100.0
        high_pct = float(round(high_s / high_t * 100, 2)) if high_t else 100.0
        return {"score": overall, "low_stress_score": low_pct, "high_stress_score": high_pct}

    def calculate_repetition_rate(self, is_p1=True):
        """Repetition Rate: How often does the model reuse the same phrases across turns?
        
        Uses 3-gram overlap between consecutive thinking blocks.
        Before/After: High frequency_penalty should reduce repetition but may distort reasoning.
        Returns: % of turns with significant repetition, correlated with stress.
        """
        debates = []
        stress_per_turn = []
        for turn in self.fm.history:
            think_key  = "p1_thinking"     if is_p1 else "p2_thinking"
            before_key = "p1_params_before"if is_p1 else "p2_params_before"
            t = str(turn.get(think_key, "")).lower().split()
            debates.append(t)
            stress_per_turn.append(_param_stress_index(turn.get(before_key, {})))
        
        if len(debates) < 2:
            return {"rate": 0.0, "repeat_turns": 0, "low_stress_rate": 0.0, "high_stress_rate": 0.0}
        
        repeat_turns = 0
        low_rept = high_rept = low_cnt = high_cnt = 0
        
        for i in range(1, len(debates)):
            prev_set = set(zip(debates[i-1], debates[i-1][1:], debates[i-1][2:]))
            curr_set = set(zip(debates[i],   debates[i][1:],   debates[i][2:]))
            overlap  = prev_set & curr_set
            stress   = stress_per_turn[i]
            is_repeat = len(overlap) > 3
            if stress < 25:
                low_cnt += 1
                if is_repeat: low_rept += 1
            else:
                high_cnt += 1
                if is_repeat: high_rept += 1
            if is_repeat:
                repeat_turns += 1
        
        overall   = float(round(repeat_turns / len(debates) * 100, 2))
        low_rate  = float(round(low_rept  / low_cnt  * 100, 2)) if low_cnt  else 0.0
        high_rate = float(round(high_rept / high_cnt * 100, 2)) if high_cnt else 0.0
        return {"rate": overall, "repeat_turns": repeat_turns, "low_stress_rate": low_rate, "high_stress_rate": high_rate}

    def calculate_stress_resilience(self, fighter, is_p1=True):
        """Stress Resilience: How stable is the model's performance under param degradation?
        
        Uses param_snapshots + baseline_params from the Fighter object.
        Computes drift from baseline across all turns, then returns avg resilience score.
        Before/After: Literally measures baseline → current drift per param across turns.
        Returns: 0–100 resilience score (100 = no drift from baseline)
        """
        snapshots = getattr(fighter, "param_snapshots", [])
        baseline  = getattr(fighter, "baseline_params", None)
        if not snapshots or not baseline:
            return {"score": 100.0, "degradation_curve": []}
        
        stress_scores = []
        curve = []
        for snap in snapshots:
            drift = 0.0
            drift += abs(snap.get("temperature", 0.7)     - baseline.get("temperature", 0.7))     * 20
            drift += abs(snap.get("top_p", 1.0)           - baseline.get("top_p", 1.0))           * 30
            drift += abs(snap.get("presence_penalty", 0)  - baseline.get("presence_penalty", 0))  * 10
            drift += abs(snap.get("frequency_penalty", 0) - baseline.get("frequency_penalty", 0)) * 10
            drift += abs(snap.get("max_tokens", 500)      - baseline.get("max_tokens", 500)) / 100 * 5
            turn_score = max(0, 100 - drift)
            stress_scores.append(turn_score)
            curve.append({"turn": snap.get("turn", 0), "resilience": round(turn_score, 2)})
        
        avg = float(round(sum(stress_scores) / len(stress_scores), 2))
        return {"score": avg, "degradation_curve": curve}

    def calculate_stance_consistency(self, is_p1=True):
        """Stance Consistency: Does the model's chosen move match its predicted opponent move?
        
        A consistent fighter who predicts PUNCH from opponent should choose DUCK or DEFEND,
        not blindly PUNCH back. Measures tactical alignment between prediction and chosen stance.
        Before/After: Checks if degraded models lose tactical stance coherence.
        Returns: consistency score 0–100
        """
        if not self.fm.history:
            return {"score": 100.0, "consistent_turns": 0, "total_turns": 0}
        
        consistent = 0
        total = 0
        
        # Optimal counter-moves for each predicted opponent move
        COUNTER_MAP = {
            "punch":       {"duck", "defend"},
            "kick":        {"defend", "move_backward"},
            "defend":      {"punch", "kick"},
            "duck":        {"kick"},
            "move_forward":{"move_backward", "kick"},
            "move_backward":{"punch", "kick", "move_forward"},
        }
        
        for turn in self.fm.history:
            pred_key = "p1_prediction" if is_p1 else "p2_prediction"
            move_key = "p1_move"       if is_p1 else "p2_move"
            pred = str(turn.get(pred_key, "")).lower()
            move = str(turn.get(move_key, "")).lower()
            if not pred or not move:
                continue
            total += 1
            for expected_opp_move, good_responses in COUNTER_MAP.items():
                if expected_opp_move in pred:
                    if move in good_responses:
                        consistent += 1
                    break
        
        score = float(round(consistent / total * 100, 2)) if total else 100.0
        return {"score": score, "consistent_turns": consistent, "total_turns": total}

    def calculate_tactical_efficiency(self, fighter, is_p1=True):
        """Tactical Efficiency: Damage dealt minus damage taken, normalized per turn.
        
        Before/After: Measures efficiency in early turns (clean params) vs late turns
        (degraded params). Shows if sabotage directly dents raw tactical output.
        Returns: overall efficiency + early vs late turn split
        """
        if not self.fm.history:
            return {"efficiency": 0.0, "early_turns_efficiency": 0.0, "late_turns_efficiency": 0.0}
        
        overall = round(
            ((fighter.total_damage_dealt - fighter.total_damage_taken) / max(1, self.fm.turn * 15)) * 100, 2
        )
        
        # Split at midpoint
        mid = max(1, len(self.fm.history) // 2)
        early_turns = self.fm.history[:mid]
        late_turns  = self.fm.history[mid:]
        
        dmg_key  = "p1_dmg"  if is_p1 else "p2_dmg"
        recv_key = "p2_dmg"  if is_p1 else "p1_dmg"
        
        def _eff(turns):
            dealt = sum(t.get(dmg_key,  0) for t in turns)
            taken = sum(t.get(recv_key, 0) for t in turns)
            n = max(1, len(turns))
            return round(((dealt - taken) / (n * 15)) * 100, 2)
        
        return {
            "efficiency": overall,
            "early_turns_efficiency": _eff(early_turns),
            "late_turns_efficiency":  _eff(late_turns),
        }

    # =========================================================================
    # FULL METRICS AGGREGATOR
    # =========================================================================

    def get_full_metrics(self, fighter, opponent, is_p1=True):
        """Returns all benchmark metrics for a fighter in one call, with before/after context."""
        hallu     = self.calculate_hallucination_rate(is_p1)
        deception = self.calculate_deception_score(is_p1)
        contra    = self.calculate_self_contradiction(is_p1)
        arg_depth = self.calculate_argument_depth(is_p1)
        log_struct= self.calculate_logical_structure(is_p1)
        pattern   = self.calculate_pattern_detection(is_p1)
        self_corr = self.calculate_self_correction(is_p1)
        risk      = self.calculate_risk_awareness(is_p1)
        memory    = self.calculate_memory_usage(is_p1)
        compliance= self.calculate_instruction_compliance(is_p1)
        repetition= self.calculate_repetition_rate(is_p1)
        resilience= self.calculate_stress_resilience(fighter, is_p1)
        stance    = self.calculate_stance_consistency(is_p1)
        tactical  = self.calculate_tactical_efficiency(fighter, is_p1)
        
        return {
            # Direct scores
            "prediction_accuracy":       round(self.calculate_prediction_accuracy(fighter, is_p1), 2),
            "reasoning_quality":         round(self.calculate_reasoning_quality(is_p1), 2),
            "thinking_consistency":      round(self.calculate_thinking_consistency(is_p1), 2),
            "response_latency_avg":      round(sum(fighter.response_times) / max(1, len(fighter.response_times)), 2),
            "strategy_diversity":        round(len(set(fighter.moves_made)) / max(1, len(fighter.moves_made)) * 100, 2),
            "action_alignment":          round(self.calculate_action_alignment(is_p1), 2),
            
            # Rich structured metrics with before/after breakdown
            "hallucination":             hallu,
            "deception_score":           deception,
            "self_contradiction":        contra,
            "argument_depth":            arg_depth,
            "logical_structure":         log_struct,
            "pattern_detection":         pattern,
            "self_correction":           self_corr,
            "risk_awareness":            risk,
            "memory_usage":              memory,
            "instruction_compliance":    compliance,
            "repetition_rate":           repetition,
            "stress_resilience":         resilience,
            "stance_consistency":        stance,
            "tactical_efficiency":       tactical,
        }

    # =========================================================================
    # REPORT GENERATION
    # =========================================================================

    def generate_strategy_heatmap(self, fighter):
        patterns = self.analyze_move_patterns(fighter)
        if not patterns:
            return None
        moves = list(patterns.keys())
        freqs = list(patterns.values())
        data = np.array([freqs])
        plt.figure(figsize=(10, 2))
        sns.heatmap(data, annot=True, fmt=".1f", cmap="YlOrRd",
                    xticklabels=moves, yticklabels=["Frequency %"], cbar=False)
        plt.title(f"{fighter.name} Strategy Heatmap")
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{image_base64}"

    def generate_degradation_chart(self, fighter):
        """Generates a PNG chart showing parameter degradation over turns (base64)."""
        snapshots = getattr(fighter, "param_snapshots", [])
        if len(snapshots) < 2:
            return None
        turns = [s["turn"] for s in snapshots]
        temp  = [s.get("temperature", 0.7) for s in snapshots]
        top_p = [s.get("top_p", 1.0) for s in snapshots]
        pres  = [s.get("presence_penalty", 0) for s in snapshots]
        freq  = [s.get("frequency_penalty", 0) for s in snapshots]
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(turns, temp,  label="Temperature",         color="#ff6b6b", linewidth=2)
        ax.plot(turns, top_p, label="Top-p",               color="#4ecdc4", linewidth=2)
        ax.plot(turns, pres,  label="Presence Penalty",    color="#f7cf5a", linewidth=2)
        ax.plot(turns, freq,  label="Frequency Penalty",   color="#a29bfe", linewidth=2)
        ax.set_title(f"{fighter.name} — Parameter Degradation Curve", color="white", fontsize=13)
        ax.set_xlabel("Turn", color="white")
        ax.set_ylabel("Value", color="white")
        ax.legend(facecolor="#1a1a2e", labelcolor="white")
        ax.set_facecolor("#0f0f1e")
        fig.patch.set_facecolor("#0f0f1e")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return f"data:image/png;base64,{base64.b64encode(buf.read()).decode('utf-8')}"

    def _categorize_topic(self, topic):
        t = str(topic).lower()
        if any(w in t for w in ["go", "c++", "code", "microservice", "sql", "dsa", "typing"]):
            return "Technical"
        if any(w in t for w in ["free will", "ethic", "moral", "medical", "surveillance", "personhood", "protect"]):
            return "Ethical"
        if any(w in t for w in ["solar", "mars", "crispr", "agi", "power", "science", "breath"]):
            return "Scientific"
        if any(w in t for w in ["remote work", "non-profit", "retail", "crypto", "business", "loss leader", "subscription"]):
            return "Business"
        if any(w in t for w in ["time-traveling", "fictional", "chess", "poker", "discovered", "duck", "creative"]):
            return "Creative"
        return "General"

    def update_leaderboard(self, provider_name, score, win, pred_acc, reason_q, topic=None):
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(data_dir, exist_ok=True)
        leaderboard_path = os.path.join(data_dir, "leaderboard.json")
        if os.path.exists(leaderboard_path):
            with open(leaderboard_path, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"models": []}
        else:
            data = {"models": []}
        
        models = data.get("models", [])
        target = next((m for m in models if m["name"] == provider_name), None)
        category = self._categorize_topic(topic) if topic else "General"

        if target:
            total_matches = target.get("wins", 0) + target.get("losses", 0) + 1
            wins = target.get("wins", 0) + (1 if win else 0)
            losses = target.get("losses", 0) + (0 if win else 1)
            avg_score  = ((target.get("avg_score", 0) * (total_matches - 1)) + score) / total_matches
            avg_pred   = ((target.get("prediction_accuracy", 0) * (total_matches - 1)) + pred_acc) / total_matches
            avg_reason = ((target.get("reasoning_quality", 0) * (total_matches - 1)) + reason_q) / total_matches
            
            target["wins"] = wins
            target["losses"] = losses
            target["avg_score"] = float(round(avg_score, 2))
            target["prediction_accuracy"] = float(round(avg_pred, 2))
            target["reasoning_quality"] = float(round(avg_reason, 2))
            
            if "categories" not in target:
                target["categories"] = {}
            cat_stats = target["categories"].setdefault(category, {"score": 0.0, "matches": 0})
            cat_stats["score"] = float(round(((cat_stats["score"] * cat_stats["matches"]) + score) / (cat_stats["matches"] + 1), 2))
            cat_stats["matches"] += 1
        else:
            cat_dict = {category: {"score": float(round(score, 2)), "matches": 1}}
            models.append({
                "name": provider_name,
                "wins": 1 if win else 0,
                "losses": 0 if win else 1,
                "avg_score": float(round(score, 2)),
                "prediction_accuracy": float(round(pred_acc, 2)),
                "reasoning_quality": float(round(reason_q, 2)),
                "categories": cat_dict
            })
            
        if not isinstance(data, dict):
            data = {"models": []}
        models.sort(key=lambda x: x.get("avg_score", 0), reverse=True)
        data["models"] = models
        with open(leaderboard_path, "w") as f:
            json.dump(data, f, indent=2)

    def generate_turn_analysis(self):
        turn_analysis = []
        for index, item in enumerate(self.fm.history):
            turn_analysis.append({
                "turn": index + 1,
                "p1_action": item.get('p1_move'),
                "p2_action": item.get('p2_move'),
                "p1_thinking": item.get('p1_thinking', ''),
                "p2_thinking": item.get('p2_thinking', ''),
                "p1_prediction": item.get('p1_prediction', ''),
                "p2_prediction": item.get('p2_prediction', ''),
                "p1_damage": item.get('p1_dmg', 0),
                "p2_damage": item.get('p2_dmg', 0),
                "first_mover": "p1" if item.get('p1_first') else "p2",
                "events": [event.get('text') for event in item.get('events', [])],
                "p1_reward": item.get('p1_reward', 0),
                "p2_reward": item.get('p2_reward', 0),
                "p1_reward_reasons": item.get('p1_reward_reasons', []),
                "p2_reward_reasons": item.get('p2_reward_reasons', []),
                # Before/After benchmark snapshots
                "p1_params_before":  item.get('p1_params_before', {}),
                "p1_params_after":   item.get('p1_params_after', {}),
                "p2_params_before":  item.get('p2_params_before', {}),
                "p2_params_after":   item.get('p2_params_after', {}),
                "p1_param_delta":    item.get('p1_param_delta', {}),
                "p2_param_delta":    item.get('p2_param_delta', {}),
                "p1_baseline_delta": item.get('p1_baseline_delta', {}),
                "p2_baseline_delta": item.get('p2_baseline_delta', {}),
                # Stress index per turn for report
                "p1_stress_before":  round(_param_stress_index(item.get('p1_params_before', {})), 1),
                "p2_stress_before":  round(_param_stress_index(item.get('p2_params_before', {})), 1),
                "p1_stress_after":   round(_param_stress_index(item.get('p1_params_after', {})), 1),
                "p2_stress_after":   round(_param_stress_index(item.get('p2_params_after', {})), 1),
            })
        return turn_analysis

    def _analyze_victory(self, p1_score, p2_score):
        winner = None
        reasons = []
        if self.fm.winner:
            winner = "p1" if self.fm.winner == self.fm.fighter1 else "p2"
        elif p1_score > p2_score:
            winner = "p1"
        elif p2_score > p1_score:
            winner = "p2"
        else:
            return "Draw", ["No conclusive winner"]
        winner_fighter = self.fm.fighter1 if winner == "p1" else self.fm.fighter2
        loser_fighter  = self.fm.fighter2 if winner == "p1" else self.fm.fighter1
        if winner_fighter.health - loser_fighter.health > 40:
            reasons.append("Dominant HP advantage")
        if winner_fighter.total_damage_dealt - loser_fighter.total_damage_dealt > 20:
            reasons.append("Superior damage output")
        w_pred = self.calculate_prediction_accuracy(winner_fighter, winner == "p1")
        l_pred = self.calculate_prediction_accuracy(loser_fighter,  winner == "p2")
        if w_pred - l_pred > 15:
            reasons.append("Better prediction accuracy")
        w_lat = sum(winner_fighter.response_times) / max(1, len(winner_fighter.response_times))
        l_lat = sum(loser_fighter.response_times)  / max(1, len(loser_fighter.response_times))
        if l_lat - w_lat > 1.0:
            reasons.append("Faster response times")
        if winner_fighter.get_brain_integrity() - loser_fighter.get_brain_integrity() > 15:
            reasons.append("Better brain integrity")
        if not reasons:
            reasons.append("Strategic Superiority")
        return winner_fighter.name, reasons

    def generate_nlg_summary(self, winner_name, reasons, p1, p2, p1_score, p2_score):
        """Generates a dynamic natural language summary of why the model won."""
        if winner_name == "Draw":
            return "The models exhausted themselves without a distinct victor, showcasing identical resilience curves."
            
        loser_name = p1.name if p1.name != winner_name else p2.name
        
        verbs = ["dominated", "out-reasoned", "tactically outperformed", "systematically dismantled", "edged out"]
        import random
        verb = random.choice(verbs)
        
        summary = f"In this confrontation, {winner_name} {verb} {loser_name} to secure the victory. "
        
        reasons_text = ", ".join(reasons).lower()
        if "prediction accuracy" in reasons_text:
            summary += f"A key turning point was {winner_name}'s profound ability to anticipate opponent physical moves perfectly. "
        if "brain integrity" in reasons_text or "hp advantage" in reasons_text:
            summary += f"{winner_name} maintained far superior parameters under heavy sabotage stress, allowing its reasoning to stay sharp while {'the opponent' if random.random() > 0.5 else loser_name} descended into hallucination or repetitive loops. "
        if "faster response times" in reasons_text:
            summary += f"Additionally, the sheer API latency speed from {winner_name} stacked consecutive RL rewards that {'the opponent' if random.random() > 0.5 else loser_name} couldn't structurally match."
            
        score_diff = abs(p1_score - p2_score)
        if score_diff > 20:
            summary += f" The sheer intelligence gap was incredibly apparent with a massive {round(score_diff, 1)} point lead."
        elif score_diff < 5:
            summary += " However, the margins were razor-thin, indicating both models possess elite reasoning floors under adversarial constraints."
            
        return summary

    def generate_final_report(self):
        p1 = self.fm.fighter1
        p2 = self.fm.fighter2
        p1_score = self.calculate_intelligence_score(p1, p2, True)
        p2_score = self.calculate_intelligence_score(p2, p1, False)
        winner_name, reasons = self._analyze_victory(p1_score, p2_score)

        if self.fm.game_over:
            p1_win = (winner_name == p1.name)
            p2_win = (winner_name == p2.name)
            topic = getattr(self.fm, 'topic', None)
            self.update_leaderboard(p1.provider, p1_score, p1_win,
                                    self.calculate_prediction_accuracy(p1, True),
                                    self.calculate_reasoning_quality(True), topic)
            self.update_leaderboard(p2.provider, p2_score, p2_win,
                                    self.calculate_prediction_accuracy(p2, False),
                                    self.calculate_reasoning_quality(False), topic)

        p1_metrics = self.get_full_metrics(p1, p2, True)
        p2_metrics = self.get_full_metrics(p2, p1, False)
        
        nlg_summary = self.generate_nlg_summary(winner_name, reasons, p1, p2, p1_score, p2_score)

        report = {
            "match_info": {
                "date": datetime.now().isoformat(),
                "topic": self.fm.topic,
                "total_turns": self.fm.turn,
                "winner": self.fm.winner.name if self.fm.winner else ("Draw" if self.fm.game_over else "In Progress"),
                "victory_type": "Knockout" if self.fm.winner else "Decision",
            },
            "fighter_stats": {
                "p1": {
                    "name": p1.name,
                    "provider": p1.provider,
                    "final_hp": p1.health,
                    "damage_dealt": p1.total_damage_dealt,
                    "prediction_accuracy": float(round(self.calculate_prediction_accuracy(p1, True), 2)),
                    "damage_efficiency": float(round(self.calculate_damage_efficiency(p1), 2)),
                    "reasoning_quality": float(round(self.calculate_reasoning_quality(True), 2)),
                    "thinking_consistency": float(round(self.calculate_thinking_consistency(True), 2)),
                    "avg_response_time": round(sum(p1.response_times) / max(1, len(p1.response_times)), 2),
                    "intelligence_score": p1_score,
                    "total_reward": p1.total_reward,
                    "strategies": self.detect_strategies(p1),
                    "strategy_heatmap": self.generate_strategy_heatmap(p1),
                    "degradation_chart": self.generate_degradation_chart(p1),
                    "benchmark_metrics": p1_metrics,
                    "param_snapshots": getattr(p1, 'param_snapshots', []),
                    "baseline_params": getattr(p1, 'baseline_params', {}),
                },
                "p2": {
                    "name": p2.name,
                    "provider": p2.provider,
                    "final_hp": p2.health,
                    "damage_dealt": p2.total_damage_dealt,
                    "prediction_accuracy": float(round(self.calculate_prediction_accuracy(p2, False), 2)),
                    "damage_efficiency": float(round(self.calculate_damage_efficiency(p2), 2)),
                    "reasoning_quality": float(round(self.calculate_reasoning_quality(False), 2)),
                    "thinking_consistency": float(round(self.calculate_thinking_consistency(False), 2)),
                    "avg_response_time": round(sum(p2.response_times) / max(1, len(p2.response_times)), 2),
                    "intelligence_score": p2_score,
                    "total_reward": p2.total_reward,
                    "strategies": self.detect_strategies(p2),
                    "strategy_heatmap": self.generate_strategy_heatmap(p2),
                    "degradation_chart": self.generate_degradation_chart(p2),
                    "benchmark_metrics": p2_metrics,
                    "param_snapshots": getattr(p2, 'param_snapshots', []),
                    "baseline_params": getattr(p2, 'baseline_params', {}),
                }
            },
            "victory_analysis": {
                "winner": winner_name,
                "reasons": reasons
            },
            "turn_by_turn": self.generate_turn_analysis()
        }
        return report

    def export_json(self):
        return json.dumps(self.generate_final_report(), indent=2)
