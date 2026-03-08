import json
from datetime import datetime

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
                total += 1
                if prediction == actual_move:
                    correct += 1
                    
        return (correct / total * 100) if total > 0 else 0.0

    def calculate_damage_efficiency(self, fighter):
        moves = len(fighter.moves_made)
        return (fighter.total_damage_dealt / moves) if moves > 0 else 0.0

    def calculate_strategic_score(self, fighter, opponent, is_p1=True):
        hp_score = fighter.health * 0.4
        damage_score = fighter.total_damage_dealt * 0.3
        
        prediction_accuracy = self.calculate_prediction_accuracy(fighter, is_p1)
        prediction_score = prediction_accuracy * 0.2
        
        avg_response = sum(fighter.response_times) / len(fighter.response_times) if fighter.response_times else 0
        opp_avg_response = sum(opponent.response_times) / len(opponent.response_times) if opponent.response_times else 0
        
        speed_advantage = max(0, ((opp_avg_response - avg_response) / opp_avg_response * 100) if opp_avg_response > 0 else 0)
        speed_score = speed_advantage * 0.1
        
        return hp_score + damage_score + prediction_score + speed_score

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

    def generate_turn_analysis(self):
        turn_analysis = []
        for index, item in enumerate(self.fm.history):
            turn_analysis.append({
                "turn": index + 1,
                "p1_action": item.get('p1_move'),
                "p2_action": item.get('p2_move'),
                "p1_damage": item.get('p1_dmg', 0),
                "p2_damage": item.get('p2_dmg', 0),
                "first_mover": "p1" if item.get('p1_first') else "p2",
                "events": [event.get('text') for event in item.get('events', [])]
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
        
        p1_score = self.calculate_strategic_score(p1, p2, True)
        p2_score = self.calculate_strategic_score(p2, p1, False)
        
        winner_name, reasons = self._analyze_victory(p1_score, p2_score)

        report = {
            "match_info": {
                "date": datetime.now().isoformat(),
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
                    "prediction_accuracy": round(self.calculate_prediction_accuracy(p1, True), 2),
                    "damage_efficiency": round(self.calculate_damage_efficiency(p1), 2),
                    "avg_response_time": round(sum(p1.response_times) / max(1, len(p1.response_times)), 2),
                    "strategic_score": round(p1_score, 2),
                    "strategies": self.detect_strategies(p1),
                },
                "p2": {
                    "name": p2.name,
                    "provider": p2.provider,
                    "final_hp": p2.health,
                    "damage_dealt": p2.total_damage_dealt,
                    "prediction_accuracy": round(self.calculate_prediction_accuracy(p2, False), 2),
                    "damage_efficiency": round(self.calculate_damage_efficiency(p2), 2),
                    "avg_response_time": round(sum(p2.response_times) / max(1, len(p2.response_times)), 2),
                    "strategic_score": round(p2_score, 2),
                    "strategies": self.detect_strategies(p2),
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
