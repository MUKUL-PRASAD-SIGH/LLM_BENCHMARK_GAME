"""
LLM Fight Club backend server.

Flask + Socket.IO powers the real-time model-vs-model boxing benchmark.
"""

import os
import threading
import time

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

try:
    from .fight_manager import FightManager
    from .llm_engine import MODELS, get_lb_dashboard
except ImportError:
    from fight_manager import FightManager
    from llm_engine import MODELS, get_lb_dashboard

load_dotenv()


app = Flask(__name__, static_folder="..", static_url_path="")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

active_fights = {}


@app.route("/")
def serve_index():
    return send_from_directory("..", "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("..", filename)


@app.route("/api/models")
def get_models():
    return jsonify(MODELS)


@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok", "fights": len(active_fights)})


@app.route("/api/lb-dashboard")
def lb_dashboard():
    return jsonify(get_lb_dashboard())


@socketio.on("connect")
def on_connect():
    sid = request.sid
    print(f"[WS] Connected: {sid}")
    emit("connected", {"sid": sid})


@socketio.on("disconnect")
def on_disconnect():
    sid = request.sid
    print(f"[WS] Disconnected: {sid}")
    if sid in active_fights:
        active_fights[sid]["running"] = False
        del active_fights[sid]


@socketio.on("start_fight")
def on_start_fight(data):
    sid = request.sid
    p1 = str(data.get("p1", "1"))
    p2 = str(data.get("p2", "2"))

    fight = FightManager(p1, p2)
    active_fights[sid] = {"fight": fight, "running": True}

    print(
        f"[FIGHT] {fight.fighter1.name} vs {fight.fighter2.name} "
        f"(room={sid})"
    )
    emit("fight_started", fight.get_initial_state())

    def loop():
        time.sleep(2.5)

        while active_fights.get(sid, {}).get("running", False):
            current = active_fights[sid]["fight"]
            if current.game_over:
                break

            socketio.emit("turn_thinking", {"turn": current.turn + 1}, to=sid)
            turn_data = current.run_turn()
            if turn_data is None:
                break

            turn_data["lb_dashboard"] = get_lb_dashboard()
            socketio.emit("turn_result", turn_data, to=sid)

            if turn_data["game_over"]:
                socketio.emit(
                    "fight_over",
                    {
                        "winner": turn_data["winner"],
                        "winner_id": turn_data.get("winner_id"),
                        "winner_position": turn_data.get("winner_position"),
                        "turns": current.turn,
                        "p1_final": current.fighter1.to_dict(),
                        "p2_final": current.fighter2.to_dict(),
                    },
                    to=sid,
                )
                break

            time.sleep(3)

        if sid in active_fights:
            active_fights[sid]["running"] = False

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()


@socketio.on("stop_fight")
def on_stop_fight():
    sid = request.sid
    if sid in active_fights:
        active_fights[sid]["running"] = False
        print(f"[FIGHT] Stopped by client: {sid}")


def _emit_sabotage_state(sid, fight, event):
    socketio.emit(
        "sabotage_update",
        {
            "p1": fight.fighter1.to_dict(),
            "p2": fight.fighter2.to_dict(),
            "event": event,
        },
        to=sid,
    )


@socketio.on("sabotage_action")
def on_sabotage_action(data):
    sid = request.sid
    if sid not in active_fights:
        return

    fight = active_fights[sid]["fight"]
    target = data.get("player")
    action = data.get("action")
    event = fight.apply_sabotage_action(target, action)
    if not event:
        return

    print(f"[SABOTAGE] {action} -> {target} (room={sid})")
    _emit_sabotage_state(sid, fight, event)


@socketio.on("crowd_action")
def on_legacy_crowd_action(data):
    legacy_map = {
        "BOO": "BOX",
        "CHEER": "RESET",
    }
    mapped_action = legacy_map.get(str(data.get("action", "")).upper())
    if not mapped_action:
        return
    on_sabotage_action({"player": data.get("player"), "action": mapped_action})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n[LLM Fight Club] Server starting on http://localhost:{port}\n")
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=True,
        allow_unsafe_werkzeug=True,
    )
