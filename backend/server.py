"""
LLM Fight Club — Backend Server
Flask + SocketIO for real-time AI boxing matches.
"""

import os
import time
import threading
from flask import Flask, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from fight_manager import FightManager
from llm_engine import MODELS, get_lb_dashboard

# --------------- Flask App ---------------
app = Flask(__name__, static_folder='..', static_url_path='')
CORS(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Active fights keyed by socket session id
active_fights = {}


# --------------- Static Routes ---------------

@app.route('/')
def serve_index():
    return send_from_directory('..', 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('..', filename)


# --------------- REST API ---------------

@app.route('/api/models')
def get_models():
    return jsonify(MODELS)


@app.route('/api/health')
def health_check():
    return jsonify({'status': 'ok', 'fights': len(active_fights)})


@app.route('/api/lb-dashboard')
def lb_dashboard():
    """Load balancer health dashboard — shows per-key health scores,
    success rates, active requests, cooldown status, etc."""
    return jsonify(get_lb_dashboard())


# --------------- WebSocket Events ---------------

@socketio.on('connect')
def on_connect():
    sid = request.sid
    print(f'[WS] Connected: {sid}')
    emit('connected', {'sid': sid})


@socketio.on('disconnect')
def on_disconnect():
    sid = request.sid
    print(f'[WS] Disconnected: {sid}')
    if sid in active_fights:
        active_fights[sid]['running'] = False
        del active_fights[sid]


@socketio.on('start_fight')
def on_start_fight(data):
    sid = request.sid
    p1 = str(data.get('p1', '1'))
    p2 = str(data.get('p2', '2'))

    name1 = MODELS.get(p1, {}).get('name', '?')
    name2 = MODELS.get(p2, {}).get('name', '?')
    print(f'[FIGHT] {name1} vs {name2}  (room={sid})')

    fight = FightManager(p1, p2)
    active_fights[sid] = {'fight': fight, 'running': True}

    emit('fight_started', fight.get_initial_state())

    # Run the fight loop in a background thread
    def loop():
        time.sleep(3)  # Let "FIGHT!" animation play

        while active_fights.get(sid, {}).get('running', False):
            fm = active_fights[sid]['fight']
            if fm.game_over:
                break

            # Emit "thinking" state so UI shows spinner
            socketio.emit('turn_thinking', {'turn': fm.turn + 1}, to=sid)

            turn_data = fm.run_turn()
            if turn_data is None:
                break

            # Attach load balancer health data to each turn
            turn_data['lb_dashboard'] = get_lb_dashboard()

            socketio.emit('turn_result', turn_data, to=sid)

            if turn_data['game_over']:
                socketio.emit('fight_over', {
                    'winner': turn_data['winner'],
                    'winner_id': turn_data.get('winner_id'),
                    'winner_position': turn_data.get('winner_position'),
                    'turns': fm.turn,
                    'p1_final': fm.fighter1.to_dict(),
                    'p2_final': fm.fighter2.to_dict(),
                }, to=sid)
                break

            # Pause between turns for animation + rate limit avoidance
            time.sleep(5)

        # Cleanup
        if sid in active_fights:
            active_fights[sid]['running'] = False

    t = threading.Thread(target=loop, daemon=True)
    t.start()


@socketio.on('stop_fight')
def on_stop_fight():
    sid = request.sid
    if sid in active_fights:
        active_fights[sid]['running'] = False
        print(f'[FIGHT] Stopped by client: {sid}')

@socketio.on('crowd_action')
def on_crowd_action(data):
    sid = request.sid
    if sid in active_fights:
        fm = active_fights[sid]['fight']
        target = data.get('player')  # 'p1' or 'p2'
        action = data.get('action')  # 'CHEER' or 'BOO'
        
        fighter = fm.fighter1 if target == 'p1' else fm.fighter2
        fighter.apply_crowd_influence(action)
        print(f'[CROWD] {action} {target} (room={sid})')
        
        # Send updated sabotage stats back immediately
        socketio.emit('sabotage_update', {
            'p1': fm.fighter1.to_dict(),
            'p2': fm.fighter2.to_dict()
        }, to=sid)


# --------------- Main ---------------

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print(f'\n🥊 LLM Fight Club Server starting on http://localhost:{port}\n')
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
