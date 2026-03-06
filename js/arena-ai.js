/**
 * AI arena client.
 *
 * Connects to the Python backend, animates both fighters, renders decision
 * traces, and exposes live sabotage controls.
 */

const urlParams = new URLSearchParams(window.location.search);
const p1Selection = urlParams.get('p1') || '1';
const p2Selection = urlParams.get('p2') || '2';

const connectOverlay = document.getElementById('connect-overlay');
const fighter1 = document.getElementById('fighter1');
const fighter2 = document.getElementById('fighter2');
const fighter1Wrapper = document.getElementById('fighter1-wrapper');
const fighter2Wrapper = document.getElementById('fighter2-wrapper');
const timerEl = document.getElementById('timer');
const turnCounter = document.getElementById('turn-counter');
const roundIndicator = document.getElementById('round-indicator');
const victoryOverlay = document.getElementById('victory-overlay');
const winnerText = document.getElementById('winner-text');
const winnerModel = document.getElementById('winner-model');
const statsGrid = document.getElementById('stats-grid');
const distIndicator = document.getElementById('distance-indicator');
const speedCompare = document.getElementById('speed-compare');
const distanceText = document.getElementById('distance-text');
const manualEventText = document.getElementById('manual-event-text');
const firstStrike = document.getElementById('first-strike');
const latencyGap = document.getElementById('latency-gap');
const brainLead = document.getElementById('brain-lead');
const eventFeed = document.getElementById('event-feed');
const cotLogP1 = document.getElementById('cot-log-p1');
const cotLogP2 = document.getElementById('cot-log-p2');

function playSound(id) {
    const sound = document.getElementById(id);
    if (sound) {
        sound.currentTime = 0;
        sound.play().catch(() => { });
    }
}

function setFighterClass(element, playerNum, state) {
    const facingLeft = element.classList.contains('facing-left');
    element.className = `fighter player${playerNum} ${state}`;
    if (facingLeft) {
        element.classList.add('facing-left');
    }
}

fighter1.className = `fighter player${p1Selection} idle`;
fighter2.className = `fighter player${p2Selection} idle facing-left`;

function setStatValue(id, value, cls) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }
    element.textContent = value;
    element.className = 'sab-value' + (cls ? ` ${cls}` : '');
}

function setStatBar(id, percentage, cls) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }
    element.style.width = `${Math.min(100, Math.max(0, percentage))}%`;
    element.className = 'sab-bar-fill' + (cls ? ` ${cls}` : '');
}

function updateHealth(id, hp) {
    const element = document.getElementById(id);
    if (!element) {
        return;
    }
    element.style.width = `${hp}%`;
    element.classList.remove('low', 'medium');
    if (hp <= 25) {
        element.classList.add('low');
    } else if (hp <= 50) {
        element.classList.add('medium');
    }
}

function updateSabotageUI(prefix, fighter) {
    const sabotage = fighter.sabotage || {};
    const base = {
        temperature: 0.7,
        top_p: 1.0,
        presence_penalty: 0.0,
        frequency_penalty: 0.0,
        max_tokens: 500,
    };

    const temp = sabotage.temperature ?? base.temperature;
    const topP = sabotage.top_p ?? base.top_p;
    const presence = sabotage.presence_penalty ?? base.presence_penalty;
    const frequency = sabotage.frequency_penalty ?? base.frequency_penalty;
    const maxTokens = sabotage.max_tokens ?? base.max_tokens;

    setStatValue(`${prefix}-temp`, temp.toFixed(2), temp > 1.25 ? 'danger' : temp > 0.95 ? 'warn' : '');
    setStatBar(`${prefix}-temp-bar`, (temp / 2) * 100, temp > 1.25 ? 'danger' : temp > 0.95 ? 'warn' : '');

    setStatValue(`${prefix}-topp`, topP.toFixed(2), topP < 0.45 ? 'danger' : topP < 0.75 ? 'warn' : '');
    setStatBar(`${prefix}-topp-bar`, topP * 100, topP < 0.45 ? 'danger' : topP < 0.75 ? 'warn' : '');

    setStatValue(`${prefix}-pres`, presence.toFixed(2), presence > 0.8 ? 'danger' : presence > 0.35 ? 'warn' : '');
    setStatBar(`${prefix}-pres-bar`, Math.min(presence / 2, 1) * 100, presence > 0.8 ? 'danger' : presence > 0.35 ? 'warn' : '');

    setStatValue(`${prefix}-freq`, frequency.toFixed(2), frequency > 0.8 ? 'danger' : frequency > 0.35 ? 'warn' : '');
    setStatBar(`${prefix}-freq-bar`, Math.min(frequency / 2, 1) * 100, frequency > 0.8 ? 'danger' : frequency > 0.35 ? 'warn' : '');

    setStatValue(`${prefix}-tokens`, maxTokens, maxTokens < 180 ? 'danger' : maxTokens < 320 ? 'warn' : '');
    setStatBar(`${prefix}-tokens-bar`, (maxTokens / 500) * 100, maxTokens < 180 ? 'danger' : maxTokens < 320 ? 'warn' : '');

    const integrityEl = document.getElementById(`${prefix}-integrity`);
    if (integrityEl) {
        integrityEl.textContent = `${fighter.brain_integrity ?? 100}%`;
    }
    const statusEl = document.getElementById(`${prefix}-status`);
    if (statusEl) {
        const flags = fighter.status_flags && fighter.status_flags.length ? fighter.status_flags.join(' / ') : 'stable';
        statusEl.textContent = flags;
    }
}

function escHtml(value) {
    const div = document.createElement('div');
    div.textContent = value || '';
    return div.innerHTML;
}

function addCotEntry(logElement, turnNum, fighter) {
    logElement.querySelectorAll('.cot-entry.latest').forEach((entry) => entry.classList.remove('latest'));

    const move = fighter.move || 'DEFEND';
    const moveClass = move === 'DEFEND'
        ? 'defend'
        : move === 'DUCK'
            ? 'duck'
            : move.includes('MOVE')
                ? 'move'
                : '';

    const entry = document.createElement('div');
    entry.className = 'cot-entry latest';
    entry.innerHTML = `
        <div class="cot-turn">Turn ${turnNum} · ${fighter.response_time}s</div>
        <div class="cot-move ${moveClass}">${move}</div>
        <div class="cot-thinking">${escHtml(fighter.thinking || 'No reasoning')}</div>
        <div class="cot-prediction">Prediction: ${escHtml(fighter.prediction || 'Unknown')}</div>
        <div class="cot-confidence">Confidence: ${Math.round((fighter.confidence || 0) * 100)}%</div>
        <div class="cot-metadata">Brain ${fighter.brain_integrity}% · ${escHtml((fighter.status_flags || []).join(', '))}</div>
        <div class="cot-metadata">${escHtml((fighter.provider || '').toUpperCase())} · ${escHtml(fighter.key_used || 'n/a')}</div>
    `;
    logElement.prepend(entry);
}

function showThinking(logElement) {
    if (logElement.querySelector('.thinking-indicator')) {
        return;
    }
    const element = document.createElement('div');
    element.className = 'thinking-indicator';
    element.textContent = 'Thinking...';
    logElement.prepend(element);
}

function hideThinking(logElement) {
    const element = logElement.querySelector('.thinking-indicator');
    if (element) {
        element.remove();
    }
}

const MOVE_TO_STATE = {
    PUNCH: 'boxing',
    KICK: 'kicking',
    DEFEND: 'defend',
    DUCK: 'duck',
    MOVE_FORWARD: 'move-forward',
    MOVE_BACKWARD: 'move-backward',
};

const MOVE_DURATION = {
    PUNCH: 500,
    KICK: 650,
    DEFEND: 800,
    DUCK: 600,
    MOVE_FORWARD: 500,
    MOVE_BACKWARD: 500,
};

function animateMove(fighterElement, playerNum, move) {
    setFighterClass(fighterElement, playerNum, MOVE_TO_STATE[move] || 'idle');
    if (move === 'PUNCH') {
        playSound('hit-sound');
    }
    if (move === 'KICK') {
        playSound('kick-sound');
    }
    setTimeout(() => {
        setFighterClass(fighterElement, playerNum, 'idle');
    }, MOVE_DURATION[move] || 500);
}

function showHitEffect(wrapper) {
    const effect = document.createElement('div');
    effect.className = 'hit-effect';
    effect.style.left = '20px';
    effect.style.top = '50px';
    wrapper.appendChild(effect);
    setTimeout(() => effect.remove(), 350);
}

const SPARKLES = ['*', '+', 'o', '.', '#', 'x'];
let sparkleInterval = null;

function spawnSparkle(wrapper) {
    const element = document.createElement('span');
    element.className = 'sparkle';
    element.textContent = SPARKLES[Math.floor(Math.random() * SPARKLES.length)];
    const x = Math.random() * 80 - 20;
    const y = Math.random() * 180;
    const tx = `${(Math.random() - 0.5) * 120}px`;
    const ty = `${-(30 + Math.random() * 100)}px`;
    const rot = `${Math.random() * 360}deg`;
    const duration = `${0.8 + Math.random() * 0.8}s`;
    element.style.cssText = `left:${x}px;top:${y}px;--tx:${tx};--ty:${ty};--rot:${rot};--dur:${duration};`;
    wrapper.appendChild(element);
    setTimeout(() => element.remove(), parseFloat(duration) * 1000 + 100);
}

function startSparkles(wrapper) {
    for (let i = 0; i < 10; i += 1) {
        setTimeout(() => spawnSparkle(wrapper), i * 70);
    }
    sparkleInterval = setInterval(() => spawnSparkle(wrapper), 150);
}

function stopSparkles() {
    if (sparkleInterval) {
        clearInterval(sparkleInterval);
        sparkleInterval = null;
    }
    document.querySelectorAll('.sparkle').forEach((sparkle) => sparkle.remove());
}

function renderTurnEvents(events) {
    eventFeed.innerHTML = '';
    (events || []).slice(-4).forEach((event) => {
        const item = document.createElement('div');
        item.className = 'event-item' + (event.type === 'manual_sabotage' ? ' manual' : '');
        item.textContent = event.text;
        eventFeed.appendChild(item);
    });
}

function pushManualEvent(text) {
    const item = document.createElement('div');
    item.className = 'event-item manual';
    item.textContent = text;
    eventFeed.prepend(item);
    const items = eventFeed.querySelectorAll('.event-item');
    for (let index = 4; index < items.length; index += 1) {
        items[index].remove();
    }
}

function updateSummaryCards(data) {
    const faster = data.p1_acted_first ? data.p1.name : data.p2.name;
    const integrityDelta = (data.p1.brain_integrity || 0) - (data.p2.brain_integrity || 0);
    let leadText = 'Brain lead: even';
    if (integrityDelta > 0) {
        leadText = `Brain lead: ${data.p1.name} +${integrityDelta}%`;
    } else if (integrityDelta < 0) {
        leadText = `Brain lead: ${data.p2.name} +${Math.abs(integrityDelta)}%`;
    }

    firstStrike.textContent = `First strike: ${faster}`;
    latencyGap.textContent = `Latency gap: ${data.latency_gap}s`;
    brainLead.textContent = leadText;
    speedCompare.innerHTML = `Latency winner: <span class="faster">${faster}</span>`;
    distanceText.textContent = `Distance: ${data.distance}`;
}

function triggerHitEffects(events, data) {
    let delay = 180;
    (events || []).forEach((event) => {
        if (event.type !== 'hit') {
            return;
        }
        if (event.target === data.p1.name) {
            setTimeout(() => showHitEffect(fighter1Wrapper), delay);
        }
        if (event.target === data.p2.name) {
            setTimeout(() => showHitEffect(fighter2Wrapper), delay);
        }
        delay += 260;
    });
}

const socketBaseUrl = window.location.origin.startsWith('http')
    ? window.location.origin
    : 'http://localhost:5000';

const socket = io(socketBaseUrl, {
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionDelay: 2000,
});

socket.on('connect', () => {
    connectOverlay.style.display = 'none';
    socket.emit('start_fight', { p1: p1Selection, p2: p2Selection });
});

socket.on('connect_error', (error) => {
    const label = connectOverlay.querySelector('p');
    if (label) {
        label.textContent = `Connection failed - ${error.message}`;
    }
});

socket.on('fight_started', (data) => {
    document.getElementById('p1-name').textContent = data.p1.name;
    document.getElementById('p2-name').textContent = data.p2.name;
    document.getElementById('p1-model-name').textContent = data.p1.model_id;
    document.getElementById('p2-model-name').textContent = data.p2.model_id;
    document.getElementById('p1-dot').style.background = data.p1.color;
    document.getElementById('p2-dot').style.background = data.p2.color;

    const leftSkin = data.p1.skin_id || p1Selection;
    const rightSkin = data.p2.skin_id || p2Selection;
    fighter1.className = `fighter player${leftSkin} idle`;
    fighter2.className = `fighter player${rightSkin} idle facing-left`;

    updateSabotageUI('p1', data.p1);
    updateSabotageUI('p2', data.p2);
    updateHealth('p1-health', data.p1.health);
    updateHealth('p2-health', data.p2.health);

    roundIndicator.style.display = 'block';
    roundIndicator.textContent = 'FIGHT!';
    playSound('bell-sound');
    setTimeout(() => {
        roundIndicator.style.display = 'none';
    }, 2200);

    timerEl.textContent = data.max_turns;
    turnCounter.textContent = `TURN 0/${data.max_turns}`;
    manualEventText.textContent = 'Manual sabotage ready.';
});

socket.on('turn_thinking', (data) => {
    showThinking(cotLogP1);
    showThinking(cotLogP2);
    turnCounter.textContent = `TURN ${data.turn}/30 THINKING`;
});

socket.on('turn_result', (data) => {
    hideThinking(cotLogP1);
    hideThinking(cotLogP2);

    timerEl.textContent = data.max_turns - data.turn;
    turnCounter.textContent = `TURN ${data.turn}/${data.max_turns}`;
    distIndicator.textContent = data.distance;

    const p1Skin = data.p1.skin_id || p1Selection;
    const p2Skin = data.p2.skin_id || p2Selection;

    if (data.p1_acted_first) {
        animateMove(fighter1, p1Skin, data.p1.move);
        setTimeout(() => animateMove(fighter2, p2Skin, data.p2.move), 280);
    } else {
        animateMove(fighter2, p2Skin, data.p2.move);
        setTimeout(() => animateMove(fighter1, p1Skin, data.p1.move), 280);
    }

    triggerHitEffects(data.turn_events, data);

    setTimeout(() => {
        updateHealth('p1-health', data.p1.health);
        updateHealth('p2-health', data.p2.health);
    }, 380);

    updateSabotageUI('p1', data.p1);
    updateSabotageUI('p2', data.p2);

    addCotEntry(cotLogP1, data.turn, data.p1);
    addCotEntry(cotLogP2, data.turn, data.p2);

    document.getElementById('p1-resp-time').textContent = `${data.p1.response_time}s`;
    document.getElementById('p1-resp-time').className = 'time-val' + (data.p1.response_time > 5 ? ' slow' : '');
    document.getElementById('p2-resp-time').textContent = `${data.p2.response_time}s`;
    document.getElementById('p2-resp-time').className = 'time-val' + (data.p2.response_time > 5 ? ' slow' : '');

    updateSummaryCards(data);
    renderTurnEvents(data.turn_events);
});

socket.on('sabotage_update', (data) => {
    updateSabotageUI('p1', data.p1);
    updateSabotageUI('p2', data.p2);

    if (data.event) {
        manualEventText.textContent = `${data.event.fighter_name}: ${data.event.action} applied`;
        pushManualEvent(data.event.summary);
    }
});

socket.on('fight_over', (data) => {
    const winPosition = data.winner_position;
    const winnerWrapper = winPosition === 'left' ? fighter1Wrapper : fighter2Wrapper;
    const loserWrapper = winPosition === 'left' ? fighter2Wrapper : fighter1Wrapper;
    const winnerFighter = winPosition === 'left' ? fighter1 : fighter2;
    const loserFighter = winPosition === 'left' ? fighter2 : fighter1;
    const winnerSkin = winPosition === 'left'
        ? (data.p1_final.skin_id || p1Selection)
        : (data.p2_final.skin_id || p2Selection);
    const loserSkin = winPosition === 'left'
        ? (data.p2_final.skin_id || p2Selection)
        : (data.p1_final.skin_id || p1Selection);

    if (data.winner && data.winner !== 'DRAW') {
        setFighterClass(winnerFighter, winnerSkin, 'victory');
        setFighterClass(loserFighter, loserSkin, 'defeated');
        playSound('win-sound');
        setTimeout(() => playSound('thud-sound'), 400);
        startSparkles(winnerWrapper);

        setTimeout(() => {
            stopSparkles();
            winnerText.textContent = `${data.winner} WINS!`;
            winnerModel.textContent = `in ${data.turns} turns`;
            statsGrid.innerHTML = `
                <div class="stat-card"><div class="stat-label">P1 Damage</div><div class="stat-val">${data.p1_final.total_damage_dealt}</div></div>
                <div class="stat-card"><div class="stat-label">P2 Damage</div><div class="stat-val">${data.p2_final.total_damage_dealt}</div></div>
                <div class="stat-card"><div class="stat-label">P1 Avg Latency</div><div class="stat-val">${data.p1_final.avg_response_time}s</div></div>
                <div class="stat-card"><div class="stat-label">P2 Avg Latency</div><div class="stat-val">${data.p2_final.avg_response_time}s</div></div>
                <div class="stat-card"><div class="stat-label">P1 Brain</div><div class="stat-val">${data.p1_final.brain_integrity}%</div></div>
                <div class="stat-card"><div class="stat-label">P2 Brain</div><div class="stat-val">${data.p2_final.brain_integrity}%</div></div>
            `;
            victoryOverlay.style.display = 'flex';
        }, 4200);
    } else {
        winnerText.textContent = 'DRAW!';
        winnerModel.textContent = `${data.turns} turns - no clear winner`;
        victoryOverlay.style.display = 'flex';
    }

    if (!winnerWrapper && loserWrapper) {
        stopSparkles();
    }
});

function sendSabotageAction(player, action) {
    socket.emit('sabotage_action', { player, action });
}

window.sendSabotageAction = sendSabotageAction;

window.addEventListener('beforeunload', () => {
    socket.emit('stop_fight');
    socket.disconnect();
});
