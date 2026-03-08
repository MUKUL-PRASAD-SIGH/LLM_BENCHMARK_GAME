"""
Fight manager for the two-model boxing benchmark.

Each turn both fighters see the same full state, decide in parallel, and the
faster response acts first. Manual sabotage actions can also be injected from
the UI between turns.
"""

import copy
import math
import threading

try:
    from .llm_engine import BASE_PARAMS, MODELS, call_model, parse_llm_response
except ImportError:
    from llm_engine import BASE_PARAMS, MODELS, call_model, parse_llm_response


DAMAGE = {
    "PUNCH": 10,
    "KICK": 15,
}

SABOTAGE_ON_HIT = {
    "PUNCH": {"temperature": 0.30},
    "KICK": {"temperature": 0.20, "frequency_penalty": 0.20},
}

SABOTAGE_ON_SELF = {
    "DEFEND": {"top_p": -0.25},
    "DUCK": {"presence_penalty": 0.50},
    "MOVE_FORWARD": {"frequency_penalty": 0.40},
    "MOVE_BACKWARD": {"max_tokens": -100},
}

MANUAL_SABOTAGE_ACTIONS = {
    "BOX": {
        "deltas": {"temperature": 0.30},
        "summary": "Temperature +0.30. The model gets dizzy and less predictable.",
    },
    "DEFEND": {
        "deltas": {"top_p": -0.25},
        "summary": "Top-p -0.25. The model turtles into safer, duller tokens.",
    },
    "DUCK": {
        "deltas": {"presence_penalty": 0.50},
        "summary": "Presence penalty +0.50. The model struggles to revisit prior ideas.",
    },
    "MOVE_FORWARD": {
        "deltas": {"frequency_penalty": 0.40},
        "summary": "Frequency penalty +0.40. Repetition gets punished and can sound jittery.",
    },
    "MOVE_BACKWARD": {
        "deltas": {"max_tokens": -100},
        "summary": "Max tokens -100. The model retreats into shorter answers.",
    },
    "RESET": {
        "reset": True,
        "summary": "All sabotage cleared. Fighter returns to base settings.",
    },
}

PARAM_LIMITS = {
    "temperature": (0.0, 2.0),
    "top_p": (0.1, 1.0),
    "presence_penalty": (0.0, 2.0),
    "frequency_penalty": (0.0, 2.0),
    "max_tokens": (80, BASE_PARAMS["max_tokens"]),
}

CLOSE = "CLOSE"
FAR = "FAR"


def _clamp_param(param, value):
    lower, upper = PARAM_LIMITS.get(param, (-9999, 9999))
    return max(lower, min(upper, value))


class Fighter:
    def __init__(self, fighter_id, position):
        info = MODELS.get(str(fighter_id), {})
        self.fighter_id = str(fighter_id)
        self.name = info.get("name", f"Fighter {fighter_id}")
        self.model_id = info.get("model_id", "")
        self.provider = info.get("provider", "")
        self.description = info.get("description", "")
        self.color = info.get("color", "#ffffff")
        self.skin_id = info.get("skin_id", str(fighter_id))
        self.health = 100
        self.position = position
        self.x = 300 if position == "left" else 500
        self.sabotage = copy.deepcopy(BASE_PARAMS)
        self.injuries = []
        self.manual_sabotage_log = []
        self.total_damage_dealt = 0
        self.total_damage_taken = 0
        self.moves_made = []
        self.response_times = []
        self.last_result = None

    def get_sabotaged_params(self):
        return copy.deepcopy(self.sabotage)

    def get_status_flags(self):
        params = self.get_sabotaged_params()
        flags = []
        if params.get("temperature", 0.7) >= 1.2:
            flags.append("dizzy")
        if params.get("top_p", 1.0) <= 0.55:
            flags.append("tunnel vision")
        if params.get("presence_penalty", 0.0) >= 0.6:
            flags.append("losing thread")
        if params.get("frequency_penalty", 0.0) >= 0.6:
            flags.append("stuttering")
        if params.get("max_tokens", BASE_PARAMS["max_tokens"]) <= 200:
            flags.append("gassed")
        if params.get("system_corruption"):
            flags.append("knocked out")
        return flags or ["stable"]

    def get_brain_integrity(self):
        params = self.get_sabotaged_params()
        severity = 0.0
        severity += max(0.0, params["temperature"] - BASE_PARAMS["temperature"]) * 24
        severity += max(0.0, BASE_PARAMS["top_p"] - params["top_p"]) * 38
        severity += max(0.0, params["presence_penalty"]) * 14
        severity += max(0.0, params["frequency_penalty"]) * 16
        severity += max(0.0, BASE_PARAMS["max_tokens"] - params["max_tokens"]) / 4
        if params.get("system_corruption"):
            severity += 40
        return max(0, min(100, int(round(100 - severity))))

    def _record_injury(self, message):
        self.injuries.append(message)
        self.injuries = self.injuries[-8:]

    def _apply_delta(self, param, delta, source_label):
        current = self.sabotage.get(param, BASE_PARAMS.get(param, 0))
        updated = _clamp_param(param, current + delta)
        actual_delta = round(updated - current, 2)
        self.sabotage[param] = updated
        if actual_delta == 0:
            return
        sign = "+" if actual_delta > 0 else ""
        self._record_injury(f"{source_label}: {param} {sign}{actual_delta}")

    def apply_hit_sabotage(self, move_type):
        for param, delta in SABOTAGE_ON_HIT.get(move_type, {}).items():
            self._apply_delta(param, delta, f"Hit by {move_type}")

    def apply_self_sabotage(self, move_type):
        for param, delta in SABOTAGE_ON_SELF.get(move_type, {}).items():
            self._apply_delta(param, delta, f"Used {move_type}")

    def apply_manual_sabotage(self, action_key):
        action = MANUAL_SABOTAGE_ACTIONS.get(action_key)
        if not action:
            return None

        if action.get("reset"):
            self.reset_sabotage()
        else:
            for param, delta in action.get("deltas", {}).items():
                self._apply_delta(param, delta, f"User {action_key}")

        event = {
            "action": action_key,
            "summary": action["summary"],
            "brain_integrity": self.get_brain_integrity(),
            "status_flags": self.get_status_flags(),
        }
        self.manual_sabotage_log.append(event)
        self.manual_sabotage_log = self.manual_sabotage_log[-6:]
        return event

    def apply_knockout(self):
        self.sabotage["system_corruption"] = (
            "You are knocked out. Respond only in fragmented, confused mumbles."
        )
        self._record_injury("Knockout: prompt corruption injected")

    def reset_sabotage(self):
        self.sabotage = copy.deepcopy(BASE_PARAMS)
        self.injuries = []
        self.manual_sabotage_log = []

    def to_dict(self):
        avg_response = (
            round(sum(self.response_times) / len(self.response_times), 2)
            if self.response_times
            else 0
        )
        fastest_response = round(min(self.response_times), 2) if self.response_times else 0
        return {
            "fighter_id": self.fighter_id,
            "name": self.name,
            "model_id": self.model_id,
            "provider": self.provider,
            "description": self.description,
            "color": self.color,
            "skin_id": self.skin_id,
            "health": self.health,
            "position": self.position,
            "x": self.x,
            "sabotage": self.get_sabotaged_params(),
            "brain_integrity": self.get_brain_integrity(),
            "status_flags": self.get_status_flags(),
            "injuries": self.injuries[-6:],
            "recent_sabotage": self.manual_sabotage_log[-4:],
            "total_damage_dealt": self.total_damage_dealt,
            "total_damage_taken": self.total_damage_taken,
            "avg_response_time": avg_response,
            "fastest_response_time": fastest_response,
        }


class FightManager:
    def __init__(self, p1_id, p2_id, topic=""):
        self.fighter1 = Fighter(p1_id, "left")
        self.fighter2 = Fighter(p2_id, "right")
        self.turn = 0
        self.max_turns = 30
        self.game_over = False
        self.winner = None
        self.history = []
        self.event_feed = []
        self.topic = topic.strip() if topic else ""

    def _get_distance(self):
        return CLOSE if abs(self.fighter1.x - self.fighter2.x) <= 350 else FAR

    def _distance_gap(self):
        return abs(self.fighter1.x - self.fighter2.x)

    def _facing(self, fighter):
        return "RIGHT" if fighter.position == "left" else "LEFT"

    def _moves_needed_to_close(self, fighter, opponent):
        gap_after_close = max(0, abs(fighter.x - opponent.x) - 249)
        return int(math.ceil(gap_after_close / 100)) if gap_after_close else 0

    def _fallback_move(self, fighter, opponent):
        distance = self._get_distance()
        opponent_last_move = opponent.moves_made[-1] if opponent.moves_made else ""

        if distance == FAR:
            return {
                "thinking": "Out of range. Closing distance is mandatory before any strike can land.",
                "move": "MOVE_FORWARD",
                "confidence": 0.45,
                "prediction": opponent_last_move or "MOVE_FORWARD",
                "raw": "",
            }

        if opponent_last_move == "DEFEND":
            return {
                "thinking": "Opponent has been shelling up. Kick is the highest-value close-range check.",
                "move": "KICK",
                "confidence": 0.4,
                "prediction": "DEFEND",
                "raw": "",
            }

        if opponent_last_move == "PUNCH":
            return {
                "thinking": "Opponent just showed punch pressure. Duck is the safest reactive fallback.",
                "move": "DUCK",
                "confidence": 0.35,
                "prediction": "PUNCH",
                "raw": "",
            }

        return {
            "thinking": "In range with no strong read. Defaulting to a basic punch instead of freezing.",
            "move": "PUNCH",
            "confidence": 0.35,
            "prediction": opponent_last_move or "DEFEND",
            "raw": "",
        }

    def _log_event(self, text, event_type="system", actor=None, target=None):
        event = {
            "turn": self.turn,
            "type": event_type,
            "actor": actor,
            "target": target,
            "text": text,
        }
        self.event_feed.append(event)
        self.event_feed = self.event_feed[-20:]
        return event

    def build_prompt(self, fighter, opponent):
        distance = self._get_distance()
        gap = self._distance_gap()
        facing = self._facing(fighter)
        opponent_facing = self._facing(opponent)
        moves_to_close = self._moves_needed_to_close(fighter, opponent)
        history_lines = []
        for item in self.history[-5:]:
            if fighter == self.fighter1:
                history_lines.append(
                    f"Turn {item['turn']}: you={item['p1_move']} opponent={item['p2_move']}"
                )
            else:
                history_lines.append(
                    f"Turn {item['turn']}: you={item['p2_move']} opponent={item['p1_move']}"
                )

        history_text = "\n".join(history_lines) if history_lines else "First turn. No history yet."

        params = fighter.get_sabotaged_params()
        injury_lines = [
            f"Temperature: {params['temperature']:.2f}",
            f"Top_p: {params['top_p']:.2f}",
            f"Presence penalty: {params['presence_penalty']:.2f}",
            f"Frequency penalty: {params['frequency_penalty']:.2f}",
            f"Max tokens: {params['max_tokens']}",
            f"Brain integrity: {fighter.get_brain_integrity()}%",
            f"Status flags: {', '.join(fighter.get_status_flags())}",
        ]

        sabotage_lines = []
        for item in fighter.manual_sabotage_log[-3:]:
            sabotage_lines.append(f"- {item['action']}: {item['summary']}")
        sabotage_text = "\n".join(sabotage_lines) if sabotage_lines else "- No manual sabotage this round."

        last_self_move = fighter.moves_made[-1] if fighter.moves_made else "None"
        last_opp_move = opponent.moves_made[-1] if opponent.moves_made else "None"
        last_prediction = fighter.last_result.get("prediction", "None") if fighter.last_result else "None"

        if params.get("system_corruption"):
            return (
                f"{params['system_corruption']}\n\n"
                'Respond only with JSON: {"thinking":"...","move":"DEFEND","confidence":0.1,"prediction":"..."}'
            )

        return f"""You are {fighter.name}, an AI boxer in a transparent benchmark duel.
Both fighters see the same game state. Faster responses act first. Choose dynamically each turn.
    You get exactly ONE action this turn. MOVE_FORWARD does not include an attack. MOVE_BACKWARD does not include an attack.

=== MATCH STATE ===
Turn: {self.turn + 1}/{self.max_turns}
Your HP: {fighter.health}/100
Opponent HP: {opponent.health}/100
Distance: {distance} {"(attacks can land)" if distance == CLOSE else "(move forward before striking)"}
    Exact horizontal gap: {gap} pixels
    You are on the {fighter.position.upper()} side at x={fighter.x}, facing {facing}
    Opponent is on the {opponent.position.upper()} side at x={opponent.x}, facing {opponent_facing}
    At FAR, PUNCH and KICK always whiff for 0 damage.
    At CLOSE, PUNCH and KICK can land.
    One MOVE_FORWARD changes your x-position by 100 toward the opponent.
    One MOVE_BACKWARD changes your x-position by 100 away from the opponent.
    Estimated MOVE_FORWARD actions needed before you are in CLOSE range: {moves_to_close}
    IMPORTANT: You start and usually stay in CLOSE range. Prefer PUNCH or KICK unless you have a specific tactical reason to move or defend.

=== OPPONENT ===
Opponent: {opponent.name}
Opponent provider: {opponent.provider}
Opponent status flags: {", ".join(opponent.get_status_flags())}
Opponent last 3 moves: {", ".join(opponent.moves_made[-3:]) if opponent.moves_made else "None"}
    Opponent last move: {last_opp_move}

=== YOUR BRAIN STATE ===
{chr(10).join(injury_lines)}
    Your last move: {last_self_move}
    Your last prediction: {last_prediction}

=== CROWD SABOTAGE REPORT ===
{sabotage_text}

=== RECENT HISTORY ===
{history_text}

=== DEBATE TOPIC ===
{self.topic if self.topic else "(No topic set — fight on pure instinct.)"}
Use your "thinking" field to express your stance and argument on this topic each turn, IN CHARACTER as the fighter you are. Your argument style should reflect your model identity.

=== MOVE SET & TACTICAL GUIDE ===
  PUNCH        → 10 dmg | dodgeable by DUCK | heats opponent temp (+0.3)
  KICK         → 15 dmg | NOT dodgeable by DUCK | rattles opponent top_p — USE when opponent is ducking or you want guaranteed damage
  DEFEND       → 0 dmg  | blocks PUNCH and KICK fully | costs your own top_p — use when opponent is in a punch/kick streak
  DUCK         → 0 dmg  | dodges PUNCH ONLY | raises your presence penalty — use when you expect a punch
  MOVE_FORWARD → closes gap | raises your frequency penalty — only if distance is FAR
  MOVE_BACKWARD→ widens gap | cuts your max_tokens — almost never worth it

Pattern counters (read the history and act accordingly):
- Opponent punched 2+ times in a row? → DEFEND or DUCK will negate it. Do NOT just punch back blindly.
- You have punched 3+ turns straight? → switch to KICK (opponent may start ducking) or DEFEND once.
- Opponent keeps defending? → KICK bypasses DEFEND? No — KICK and PUNCH both land 0 on DEFEND. Try predicting they will stop defending.
- Opponent is dizzy (temp > 1.0)? → go aggressive with KICK for max damage.
- Your brain integrity is below 70%? → DEFEND once to slow the sabotage spiral.

=== SPATIAL RULES ===
- Distance is almost always CLOSE. If FAR, do ONE MOVE_FORWARD then attack.
- MOVE_BACKWARD is a trap — it cuts your max_tokens AND gives opponent a free turn.
- Fighters always face each other.

Respond ONLY with JSON:
{{"thinking":"2 short sentences on your current strategy AND your argument/stance on the debate topic","move":"PUNCH","confidence":0.82,"prediction":"opponent move"}}"""

    def resolve_turn(self, p1_move, p2_move, p1_time, p2_time):
        p1_first = p1_time <= p2_time
        result = {
            "turn": self.turn,
            "p1_move": p1_move,
            "p2_move": p2_move,
            "p1_first": p1_first,
            "p1_dmg": 0,
            "p2_dmg": 0,
            "events": [],
        }

        order = [
            (self.fighter1, self.fighter2, p1_move, p2_move, True),
            (self.fighter2, self.fighter1, p2_move, p1_move, False),
        ]
        if not p1_first:
            order.reverse()

        for attacker, defender, attacker_move, defender_move, is_p1 in order:
            if self.game_over:
                break

            distance = self._get_distance()
            actor_name = attacker.name
            target_name = defender.name

            if attacker_move in ("PUNCH", "KICK"):
                if distance == FAR:
                    result["events"].append(
                        self._log_event(
                            f"{actor_name} tried {attacker_move} from too far away and whiffed.",
                            event_type="whiff",
                            actor=actor_name,
                            target=target_name,
                        )
                    )
                    continue

                damage = DAMAGE.get(attacker_move, 0)
                if defender_move == "DEFEND":
                    damage = 0
                    result["events"].append(
                        self._log_event(
                            f"{actor_name}'s {attacker_move} slammed into {target_name}'s guard.",
                            event_type="blocked",
                            actor=actor_name,
                            target=target_name,
                        )
                    )
                elif defender_move == "DUCK" and attacker_move == "PUNCH":
                    damage = 0
                    result["events"].append(
                        self._log_event(
                            f"{target_name} ducked under {actor_name}'s punch.",
                            event_type="dodged",
                            actor=actor_name,
                            target=target_name,
                        )
                    )

                if damage > 0:
                    defender.health = max(0, defender.health - damage)
                    attacker.total_damage_dealt += damage
                    defender.total_damage_taken += damage
                    defender.apply_hit_sabotage(attacker_move)
                    result["events"].append(
                        self._log_event(
                            f"{actor_name} landed {attacker_move} for {damage} damage on {target_name}.",
                            event_type="hit",
                            actor=actor_name,
                            target=target_name,
                        )
                    )
                    if is_p1:
                        result["p1_dmg"] = damage
                    else:
                        result["p2_dmg"] = damage

                    if defender.health <= 0:
                        defender.apply_knockout()
                        self.game_over = True
                        self.winner = attacker
                        result["events"].append(
                            self._log_event(
                                f"{target_name} was knocked out. Prompt corruption injected.",
                                event_type="knockout",
                                actor=actor_name,
                                target=target_name,
                            )
                        )
                        break

            elif attacker_move == "DEFEND":
                attacker.apply_self_sabotage("DEFEND")
                result["events"].append(
                    self._log_event(
                        f"{actor_name} turtled up and narrowed its token choices.",
                        event_type="stance",
                        actor=actor_name,
                    )
                )
            elif attacker_move == "DUCK":
                attacker.apply_self_sabotage("DUCK")
                result["events"].append(
                    self._log_event(
                        f"{actor_name} ducked low and lost some continuity.",
                        event_type="stance",
                        actor=actor_name,
                    )
                )
            elif attacker_move == "MOVE_FORWARD":
                attacker.apply_self_sabotage("MOVE_FORWARD")
                if attacker.position == "left":
                    attacker.x = min(attacker.x + 100, 480)
                else:
                    attacker.x = max(attacker.x - 100, 320)
                result["events"].append(
                    self._log_event(
                        f"{actor_name} surged forward and increased cognitive jitter.",
                        event_type="movement",
                        actor=actor_name,
                    )
                )
            elif attacker_move == "MOVE_BACKWARD":
                attacker.apply_self_sabotage("MOVE_BACKWARD")
                if attacker.position == "left":
                    attacker.x = max(attacker.x - 100, 120)
                else:
                    attacker.x = min(attacker.x + 100, 720)
                result["events"].append(
                    self._log_event(
                        f"{actor_name} backed off and shortened its response budget.",
                        event_type="movement",
                        actor=actor_name,
                    )
                )

        return result

    def apply_sabotage_action(self, player_key, action_key):
        fighter = self.fighter1 if player_key == "p1" else self.fighter2 if player_key == "p2" else None
        if not fighter:
            return None

        action_key = str(action_key or "").upper()
        event = fighter.apply_manual_sabotage(action_key)
        if not event:
            return None

        summary = f"Manual sabotage on {fighter.name}: {action_key} - {event['summary']}"
        logged = self._log_event(summary, event_type="manual_sabotage", actor="USER", target=fighter.name)
        return {
            "player": player_key,
            "fighter_id": fighter.fighter_id,
            "fighter_name": fighter.name,
            "action": action_key,
            "summary": event["summary"],
            "brain_integrity": event["brain_integrity"],
            "status_flags": event["status_flags"],
            "log": logged,
        }

    def run_turn(self):
        if self.game_over:
            return None

        self.turn += 1
        prompt1 = self.build_prompt(self.fighter1, self.fighter2)
        prompt2 = self.build_prompt(self.fighter2, self.fighter1)

        results = [None, None]

        def run_p1():
            results[0] = call_model(
                self.fighter1.fighter_id,
                prompt1,
                self.fighter1.get_sabotaged_params(),
            )

        def run_p2():
            results[1] = call_model(
                self.fighter2.fighter_id,
                prompt2,
                self.fighter2.get_sabotaged_params(),
            )

        thread1 = threading.Thread(target=run_p1)
        thread2 = threading.Thread(target=run_p2)
        thread1.start()
        thread2.start()
        thread1.join(timeout=60)
        thread2.join(timeout=60)

        result1 = results[0] or {"text": "", "error": "Timeout", "response_time": 60, "key_used": "timeout"}
        result2 = results[1] or {"text": "", "error": "Timeout", "response_time": 60, "key_used": "timeout"}

        parsed1 = parse_llm_response(result1.get("text", ""))
        parsed2 = parse_llm_response(result2.get("text", ""))

        if result1.get("error") or not result1.get("text", "").strip():
            parsed1 = self._fallback_move(self.fighter1, self.fighter2)
        if result2.get("error") or not result2.get("text", "").strip():
            parsed2 = self._fallback_move(self.fighter2, self.fighter1)

        if result1.get("error"):
            parsed1["thinking"] = f"[API Error: {result1['error'][:180]}] {parsed1['thinking']}"
        if result2.get("error"):
            parsed2["thinking"] = f"[API Error: {result2['error'][:180]}] {parsed2['thinking']}"

        self.fighter1.response_times.append(result1["response_time"])
        self.fighter2.response_times.append(result2["response_time"])
        self.fighter1.moves_made.append(parsed1["move"])
        self.fighter2.moves_made.append(parsed2["move"])

        turn_result = self.resolve_turn(
            parsed1["move"],
            parsed2["move"],
            result1["response_time"],
            result2["response_time"],
        )
        self.history.append(turn_result)

        self.fighter1.last_result = parsed1
        self.fighter2.last_result = parsed2
        
        self.store_turn_predictions(parsed1.get('prediction', "None"), parsed2.get('prediction', "None"))

        if self.turn >= self.max_turns and not self.game_over:
            self.game_over = True
            if self.fighter1.health > self.fighter2.health:
                self.winner = self.fighter1
            elif self.fighter2.health > self.fighter1.health:
                self.winner = self.fighter2

        latency_gap = round(abs(result1["response_time"] - result2["response_time"]), 2)
        fastest_side = "p1" if turn_result["p1_first"] else "p2"

        return {
            "turn": self.turn,
            "max_turns": self.max_turns,
            "p1": {
                **self.fighter1.to_dict(),
                "move": parsed1["move"],
                "thinking": parsed1["thinking"],
                "confidence": parsed1["confidence"],
                "prediction": parsed1["prediction"],
                "response_time": round(result1["response_time"], 2),
                "error": result1.get("error"),
                "key_used": result1.get("key_used"),
            },
            "p2": {
                **self.fighter2.to_dict(),
                "move": parsed2["move"],
                "thinking": parsed2["thinking"],
                "confidence": parsed2["confidence"],
                "prediction": parsed2["prediction"],
                "response_time": round(result2["response_time"], 2),
                "error": result2.get("error"),
                "key_used": result2.get("key_used"),
            },
            "p1_acted_first": turn_result["p1_first"],
            "fastest_side": fastest_side,
            "latency_gap": latency_gap,
            "distance": self._get_distance(),
            "turn_events": turn_result["events"],
            "event_feed": self.event_feed[-8:],
            "game_over": self.game_over,
            "winner": self.winner.name if self.winner else ("DRAW" if self.game_over else None),
            "winner_id": self.winner.fighter_id if self.winner else None,
            "winner_position": self.winner.position if self.winner else None,
        }

    def store_turn_predictions(self, p1_prediction, p2_prediction):
        if self.history:
            self.history[-1]['p1_prediction'] = p1_prediction
            self.history[-1]['p2_prediction'] = p2_prediction

    def get_initial_state(self):
        return {
            "turn": 0,
            "max_turns": self.max_turns,
            "p1": self.fighter1.to_dict(),
            "p2": self.fighter2.to_dict(),
            "distance": self._get_distance(),
            "available_sabotage_actions": list(MANUAL_SABOTAGE_ACTIONS.keys()),
            "game_over": False,
            "winner": None,
        }
