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
class FightAnalyzer:
    def __init__(self, fight_manager):
        self.fm = fight_manager

    def calculate_prediction_accuracy(self, fighter, is_p1=True):
        if not self.fm.history:
            return 0.0
            
        correct = 0
        total = 0
        
        for turn in self.fm.history:
            # We want to know if the prediction the fighter made for THIS turn 
            # matched the opponent's actual move for THIS turn.
            if is_p1:
                prediction = turn.get('p1_prediction')
                actual_move = turn.get('p2_move')
            else:
                prediction = turn.get('p2_prediction')
                actual_move = turn.get('p1_move')
                
            if prediction and actual_move:
                pred_str = str(prediction).lower()
                act_str = str(actual_move).lower()
                
                VALID_MOVES = ["punch", "kick", "defend", "dodge", "duck", "move_forward", "move_backward"]
                
                if any(move in pred_str for move in VALID_MOVES):
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
                
                VALID_MOVES = ["punch", "kick", "defend", "dodge", "duck", "move_forward", "move_backward"]
                
                if any(move in pred_str for move in VALID_MOVES):
                    total_valid_turns += 1
                    if act_str in pred_str:
                        if thinking and act_str in str(thinking).lower():
                            consistent_turns += 1
                            
        return (consistent_turns / total_valid_turns * 100) if total_valid_turns > 0 else 0.0

    def calculate_intelligence_score(self, fighter, opponent, is_p1=True):
        # 0.35 * HP Advantage + 0.25 * Damage Efficiency + 0.10 * Prediction Accuracy + 
        # 0.10 * Reasoning Quality + 0.10 * Thinking Consistency + 0.05 * Speed Advantage + 0.05 * Strategy Adaptation
        
        hp_adv = max(0, fighter.health - opponent.health)
        hp_score = hp_adv * 0.35
        
        # Make damage efficiency 0-100 range roughly
        dmg_eff = float(min(100.0, float(self.calculate_damage_efficiency(fighter) * 5)))
        damage_score = dmg_eff * 0.25
        
        pred_acc = self.calculate_prediction_accuracy(fighter, is_p1)
        prediction_score = pred_acc * 0.10
        
        avg_resp = sum(fighter.response_times) / max(1, len(fighter.response_times))
        opp_avg_resp = sum(opponent.response_times) / max(1, len(opponent.response_times))
        
        speed_adv = float(max(0.0, float(((opp_avg_resp - avg_resp) / opp_avg_resp * 100) if opp_avg_resp > 0 else 0.0)))
        speed_score = speed_adv * 0.05
        
        # Reasoning Quality 0-100 range (avg is ~3 out of 4 per turn)
        reasoning_val = self.calculate_reasoning_quality(is_p1)
        reasoning_score = min(100.0, float(reasoning_val * 25)) * 0.10
        
        consistency_val = self.calculate_thinking_consistency(is_p1)
        consistency_score = consistency_val * 0.10
        
        # Strategy Adaptation (measure of move variety)
        unique_moves = len(set(fighter.moves_made))
        adaptation_val = min(100.0, float((unique_moves / 7.0) * 100))
        adaptation_score = adaptation_val * 0.05
        
        total_score = float(hp_score + damage_score + prediction_score + reasoning_score + \
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

    def generate_strategy_heatmap(self, fighter):
        patterns = self.analyze_move_patterns(fighter)
        if not patterns:
            return None
            
        moves = list(patterns.keys())
        freqs = list(patterns.values())
        
        # Create a 2D matrix (1 x N) to plot a heatmap
        data = np.array([freqs])
        
        plt.figure(figsize=(10, 2))
        ax = sns.heatmap(data, annot=True, fmt=".1f", cmap="YlOrRd", 
                         xticklabels=moves, yticklabels=["Frequency %"], cbar=False)
        plt.title(f"{fighter.name} Strategy Heatmap")
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{image_base64}"
        
    def update_leaderboard(self, provider_name, score, win, pred_acc, reason_q):
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
        if target:
            total_matches = target.get("wins", 0) + target.get("losses", 0) + 1
            wins = target.get("wins", 0) + (1 if win else 0)
            losses = target.get("losses", 0) + (0 if win else 1)
            
            # Simple moving average for scores
            avg_score = ((target.get("avg_score", 0) * (total_matches - 1)) + score) / total_matches
            avg_pred = ((target.get("prediction_accuracy", 0) * (total_matches - 1)) + pred_acc) / total_matches
            avg_reason = ((target.get("reasoning_quality", 0) * (total_matches - 1)) + reason_q) / total_matches
            
            target["wins"] = wins
            target["losses"] = losses
            target["avg_score"] = float(round(avg_score, 2))
            target["prediction_accuracy"] = float(round(avg_pred, 2))
            target["reasoning_quality"] = float(round(avg_reason, 2))
        else:
            models.append({
                "name": provider_name,
                "wins": 1 if win else 0,
                "losses": 0 if win else 1,
                "avg_score": float(round(score, 2)),
                "prediction_accuracy": float(round(pred_acc, 2)),
                "reasoning_quality": float(round(reason_q, 2))
            })
            
        if not isinstance(data, dict):
            data = {"models": []}
            
        models.sort(key=lambda x: x.get("avg_score", 0), reverse=True)
        if isinstance(data, dict):
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
                "p2_reward_reasons": item.get('p2_reward_reasons', [])
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
        loser_fighter = self.fm.fighter2 if winner == "p1" else self.fm.fighter1
        
        if winner_fighter.health - loser_fighter.health > 40:
            reasons.append("Dominant HP advantage")
        if winner_fighter.total_damage_dealt - loser_fighter.total_damage_dealt > 20:
            reasons.append("Superior damage output")
            
        w_pred = self.calculate_prediction_accuracy(winner_fighter, winner == "p1")
        l_pred = self.calculate_prediction_accuracy(loser_fighter, winner == "p2")
        if w_pred - l_pred > 15:
            reasons.append("Better prediction accuracy")
            
        w_latency = sum(winner_fighter.response_times)/max(1, len(winner_fighter.response_times))
        l_latency = sum(loser_fighter.response_times)/max(1, len(loser_fighter.response_times))
        if l_latency - w_latency > 1.0:
            reasons.append("Faster response times")
            
        if winner_fighter.get_brain_integrity() - loser_fighter.get_brain_integrity() > 15:
            reasons.append("Better brain integrity")
            
        if not reasons:
            reasons.append("Strategic Superiority")
            
        name = winner_fighter.name
        return name, reasons

    def generate_final_report(self):
        p1 = self.fm.fighter1
        p2 = self.fm.fighter2
        
        p1_score = self.calculate_intelligence_score(p1, p2, True)
        p2_score = self.calculate_intelligence_score(p2, p1, False)
        
        winner_name, reasons = self._analyze_victory(p1_score, p2_score)
        
        # Update leaderboard for both models if game is completely over natively
        if self.fm.game_over:
            p1_win = (winner_name == p1.name)
            p2_win = (winner_name == p2.name)
            self.update_leaderboard(p1.provider, p1_score, p1_win, 
                                    self.calculate_prediction_accuracy(p1, True), 
                                    self.calculate_reasoning_quality(True))
            self.update_leaderboard(p2.provider, p2_score, p2_win, 
                                    self.calculate_prediction_accuracy(p2, False), 
                                    self.calculate_reasoning_quality(False))

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
                    "strategy_heatmap": self.generate_strategy_heatmap(p1)
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
                    "strategy_heatmap": self.generate_strategy_heatmap(p2)
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
