/**
 * AI arena client — clean flat structure, no nested initSocket wrapper.
 */

// ─── URL params ─────────────────────────────────────────────────────────────
const urlParams = new URLSearchParams(window.location.search);
const p1Selection = urlParams.get('p1') || '1';
const p2Selection = urlParams.get('p2') || '2';

let fightTopic = '';
let socket = null;

function setTopic(text) {
    const input = document.getElementById('topic-input');
    if (input) input.value = text;
}

function beginFight() {
    const input = document.getElementById('topic-input');
    const raw = input ? input.value.trim() : '';
    // Use default topic if nothing entered
    fightTopic = raw || 'Who is the superior intelligence?';

    // Show the topic banner in the arena
    const banner = document.getElementById('topic-banner');
    if (banner) {
        banner.textContent = '\u2694 TOPIC: ' + fightTopic;
        banner.style.display = 'block';
    }

    // Swap modal -> connect overlay
    document.getElementById('topic-modal').style.display = 'none';
    document.getElementById('connect-overlay').style.display = 'flex';

    try {
        initSocket();
    } catch (err) {
        document.getElementById('connect-overlay').style.display = 'none';
        document.getElementById('topic-modal').style.display = 'flex';
        alert('Failed to start fight: ' + err.message);
    }
}

window.setTopic = setTopic;
window.beginFight = beginFight;

// Allow pressing Enter in the topic input
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('topic-input');
    if (input) input.addEventListener('keydown', (e) => { if (e.key === 'Enter') beginFight(); });
});

function initSocket() {
const FALLBACK_SKINS = {
    '1': '1',
    '2': '2',
    '3': '3',
    '4': '4',
    '5': '1',
    '6': '2',
};

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

fighter1.className = `fighter player${FALLBACK_SKINS[p1Selection] || '1'} idle`;
fighter2.className = `fighter player${FALLBACK_SKINS[p2Selection] || '2'} idle facing-left`;

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
    const currentWidth = parseFloat(element.style.width) || 100;
    if (hp < currentWidth) {
        // Flash the health bar container
        const container = element.parentElement;
        container.classList.add('flash-hp');
        setTimeout(() => container.classList.remove('flash-hp'), 300);
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
    
    // Add action floating text on the attacker
    const wrapper = fighterElement.parentElement;
    if (move === 'PUNCH') {
        playSound('hit-sound');
        showFloatingText(wrapper, 'PUNCH!', 'block');
    } else if (move === 'KICK') {
        playSound('kick-sound');
        showFloatingText(wrapper, 'KICK!', 'block');
    } else if (move === 'DUCK') {
        showFloatingText(wrapper, 'DUCK', 'whiff');
    } else if (move === 'DEFEND') {
        showFloatingText(wrapper, 'GUARD', 'block');
    }
    
    if (['MOVE_FORWARD', 'MOVE_BACKWARD'].includes(move)) {
        showFloatingText(wrapper, 'DASH', 'whiff');
    }

    setTimeout(() => {
        setFighterClass(fighterElement, playerNum, 'idle');
    }, MOVE_DURATION[move] || 500);
}

function showHitEffect(wrapper) {
    // Basic hit burst effect
    const effect = document.createElement('div');
    effect.className = 'hit-effect custom-hit';
    // Add random slight offset for variety
    const offsetX = Math.random() * 20 - 10;
    const offsetY = Math.random() * 20 - 10;
    effect.style.left = `calc(50% + ${offsetX}px)`;
    effect.style.top = `calc(30% + ${offsetY}px)`;
    wrapper.appendChild(effect);
    setTimeout(() => effect.remove(), 350);
}

function showFloatingText(wrapper, text, type) {
    const el = document.createElement('div');
    el.className = `floating-text ${type}`;
    el.textContent = text;
    // Position it slightly randomly
    const offsetX = Math.random() * 40 - 20;
    el.style.left = `calc(50% + ${offsetX}px)`;
    el.style.top = '20%';
    wrapper.appendChild(el);
    
    // Remove after animation completes
    setTimeout(() => {
        el.remove();
    }, 1000);
}

function triggerArenaShake(intensity = 'light') {
    const arena = document.querySelector('.fight-arena');
    if (!arena) return;
    arena.classList.remove('shake-light', 'shake-heavy', 'shake-massive');
    // Force a reflow to allow restarting the animation
    void arena.offsetWidth;
    arena.classList.add(`shake-${intensity}`);
    setTimeout(() => {
        arena.classList.remove(`shake-${intensity}`);
    }, 600);
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

function updateFighterPositions(p1x, p2x) {
    const arena = document.getElementById('fight-arena');
    const f1Wrapper = document.getElementById('fighter1-wrapper');
    const f2Wrapper = document.getElementById('fighter2-wrapper');
    if (!arena || !f1Wrapper || !f2Wrapper) return;
    const W = arena.offsetWidth || 840;
    const VISUAL_SPAN = W * 0.55;
    const ORIGIN = (W - VISUAL_SPAN) / 2;
    const BACK_MIN = 120, BACK_MAX = 720;
    const f1Left = ORIGIN + ((p1x - BACK_MIN) / (BACK_MAX - BACK_MIN)) * VISUAL_SPAN;
    const f2Left = ORIGIN + ((p2x - BACK_MIN) / (BACK_MAX - BACK_MIN)) * VISUAL_SPAN;
    f1Wrapper.style.left = `${Math.round(f1Left)}px`;
    f1Wrapper.style.right = 'auto';
    f2Wrapper.style.left = `${Math.round(f2Left)}px`;
    f2Wrapper.style.right = 'auto';
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
        const isTargetP1 = event.target === data.p1.name;
        const targetWrapper = isTargetP1 ? fighter1Wrapper : fighter2Wrapper;
        const targetFighter = isTargetP1 ? fighter1 : fighter2;
        
        setTimeout(() => {
            if (event.type === 'hit') {
                showHitEffect(targetWrapper);
                targetFighter.classList.add('hit');
                setTimeout(() => targetFighter.classList.remove('hit'), 300);
                
                const match = event.text.match(/for (\d+) damage/);
                const damage = match ? parseInt(match[1], 10) : 0;
                
                if (damage >= 20) {
                    playSound('hit-sound');
                    const dmgText = `-${damage}`;
                    showFloatingText(targetWrapper, 'CRITICAL HIT!', 'critical');
                    setTimeout(() => showFloatingText(targetWrapper, dmgText, 'damage massive'), 150);
                    triggerArenaShake('massive');
                    
                    const arena = document.querySelector('.fight-arena');
                    if (arena) {
                        arena.classList.add('flash-critical');
                        setTimeout(() => arena.classList.remove('flash-critical'), 500);
                    }
                } else {
                    const dmgText = match ? `-${damage}` : 'BAM!';
                    showFloatingText(targetWrapper, dmgText, 'damage');
                    triggerArenaShake('heavy');
                }
            } else if (event.type === 'blocked') {
                showFloatingText(targetWrapper, 'BLOCKED!', 'block');
                triggerArenaShake('light');
            } else if (event.type === 'dodged') {
                showFloatingText(targetWrapper, 'DODGED!', 'dodge');
            } else if (event.type === 'whiff') {
                const attackerWrapper = event.actor === data.p1.name ? fighter1Wrapper : fighter2Wrapper;
                showFloatingText(attackerWrapper, 'MISS!', 'whiff');
            }
        }, delay);

        if (['hit', 'blocked', 'dodged', 'whiff'].includes(event.type)) {
            delay += 260; // stagger multiple hits
        }
    });
}

const socketBaseUrl = window.location.origin.startsWith('http')
    ? window.location.origin
    : 'http://localhost:5000';

    let fightStarted = false;

    socket = io(socketBaseUrl, {
        transports: ['websocket', 'polling'],
        reconnection: false,
    });

    socket.on('connect', () => {
        connectOverlay.style.display = 'none';
        if (!fightStarted) {
            fightStarted = true;
            socket.emit('start_fight', { p1: p1Selection, p2: p2Selection, topic: fightTopic });
        }
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

    const leftSkin = data.p1.skin_id || FALLBACK_SKINS[p1Selection] || '1';
    const rightSkin = data.p2.skin_id || FALLBACK_SKINS[p2Selection] || '2';
    fighter1.className = `fighter player${leftSkin} idle`;
    fighter2.className = `fighter player${rightSkin} idle facing-left`;

    updateSabotageUI('p1', data.p1);
    updateSabotageUI('p2', data.p2);
    updateHealth('p1-health', data.p1.health);
    updateHealth('p2-health', data.p2.health);
    if (data.p1.x != null && data.p2.x != null) updateFighterPositions(data.p1.x, data.p2.x);

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

    const p1Skin = data.p1.skin_id || FALLBACK_SKINS[p1Selection] || '1';
    const p2Skin = data.p2.skin_id || FALLBACK_SKINS[p2Selection] || '2';

    if (data.p1_acted_first) {
        animateMove(fighter1, p1Skin, data.p1.move);
        setTimeout(() => animateMove(fighter2, p2Skin, data.p2.move), 280);
    } else {
        animateMove(fighter2, p2Skin, data.p2.move);
        setTimeout(() => animateMove(fighter1, p1Skin, data.p1.move), 280);
    }
    
    // Update visual positions across the ring based on x coordinates provided
    // Virtual center is 420 as p1=220 and p2=620
    if (data.p1 && data.p1.x !== undefined) {
        const offset = data.p1.x - 420;
        fighter1Wrapper.style.left = `calc(50% + ${offset}px)`;
    }
    if (data.p2 && data.p2.x !== undefined) {
        const offset = data.p2.x - 420;
        // override default right% style so left animation works
        fighter2Wrapper.style.right = 'auto'; 
        fighter2Wrapper.style.left = `calc(50% + ${offset - 64}px)`; // slight offset for fighter width
    }

    triggerHitEffects(data.turn_events, data);

    setTimeout(() => {
        updateHealth('p1-health', data.p1.health);
        updateHealth('p2-health', data.p2.health);
    }, 380);

    updateSabotageUI('p1', data.p1);
    updateSabotageUI('p2', data.p2);
    if (data.p1.x != null && data.p2.x != null) updateFighterPositions(data.p1.x, data.p2.x);

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
        ? (data.p1_final.skin_id || FALLBACK_SKINS[p1Selection] || '1')
        : (data.p2_final.skin_id || FALLBACK_SKINS[p2Selection] || '2');
    const loserSkin = winPosition === 'left'
        ? (data.p2_final.skin_id || FALLBACK_SKINS[p2Selection] || '2')
        : (data.p1_final.skin_id || FALLBACK_SKINS[p1Selection] || '1');

    if (data.winner && data.winner !== 'DRAW') {
        setFighterClass(winnerFighter, winnerSkin, 'victory');
        setFighterClass(loserFighter, loserSkin, 'defeated');
        playSound('win-sound');
        setTimeout(() => playSound('thud-sound'), 400);
        startSparkles(winnerWrapper);

        setTimeout(async () => {
            stopSparkles();
            winnerText.textContent = `${data.winner} WINS!`;
            winnerModel.textContent = `in ${data.turns} turns`;

            try {
                const res = await fetch(`${socketBaseUrl}/api/download_report/${socket.id}`);
                const reportData = await res.json();
                if (reportData.analysis_report) {
                    const report = reportData.analysis_report;
                    window.fightReport = report;
                    const p1Stats = report.fighter_stats.p1;
                    const p2Stats = report.fighter_stats.p2;
                    statsGrid.innerHTML = `
                        <div class="stat-card"><div class="stat-label">P1 Damage</div><div class="stat-val">${p1Stats.damage_dealt}</div></div>
                        <div class="stat-card"><div class="stat-label">P2 Damage</div><div class="stat-val">${p2Stats.damage_dealt}</div></div>
                        <div class="stat-card"><div class="stat-label">P1 Prediction</div><div class="stat-val">${p1Stats.prediction_accuracy}%</div></div>
                        <div class="stat-card"><div class="stat-label">P2 Prediction</div><div class="stat-val">${p2Stats.prediction_accuracy}%</div></div>
                        <div class="stat-card"><div class="stat-label">P1 Avg Latency</div><div class="stat-val">${p1Stats.avg_response_time}s</div></div>
                        <div class="stat-card"><div class="stat-label">P2 Avg Latency</div><div class="stat-val">${p2Stats.avg_response_time}s</div></div>
                        <div class="stat-card full-width"><div class="stat-label">Victory Reason</div><div class="stat-val small">${report.victory_analysis.reasons.join(', ')}</div></div>
                    `;
                    
                    const pdfBtn = document.getElementById('download-pdf-btn');
                    if (pdfBtn) pdfBtn.style.display = 'inline-block';
                }
            } catch (err) {
                console.error("Failed to fetch post-match report", err);
                statsGrid.innerHTML = `
                    <div class="stat-card"><div class="stat-label">P1 Damage</div><div class="stat-val">${data.p1_final.total_damage_dealt}</div></div>
                    <div class="stat-card"><div class="stat-label">P2 Damage</div><div class="stat-val">${data.p2_final.total_damage_dealt}</div></div>
                    <div class="stat-card"><div class="stat-label">P1 Avg Latency</div><div class="stat-val">${data.p1_final.avg_response_time}s</div></div>
                    <div class="stat-card"><div class="stat-label">P2 Avg Latency</div><div class="stat-val">${data.p2_final.avg_response_time}s</div></div>
                `;
            }
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

    window.addEventListener('beforeunload', () => {
        socket.emit('stop_fight');
        socket.disconnect();
    });
} // end initSocket()

function sendSabotageAction(player, action) {
    if (socket) socket.emit('sabotage_action', { player, action });
}

window.sendSabotageAction = sendSabotageAction;

window.downloadPDFReport = function() {
    if (!window.fightReport) return;
    
    if (!window.jspdf || !window.jspdf.jsPDF) {
        alert("PDF Library not loaded.");
        return;
    }
    
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const report = window.fightReport;
    
    doc.setFontSize(20);
    doc.text("LLM Fight Club - Official Match Report", 10, 20);
    
    doc.setFontSize(12);
    doc.text(`Date: ${new Date(report.match_info.date).toLocaleString()}`, 10, 30);
    doc.text(`Winner: ${report.match_info.winner}`, 10, 38);
    doc.text(`Victory Type: ${report.match_info.victory_type}`, 10, 46);
    doc.text(`Total Turns: ${report.match_info.total_turns}`, 10, 54);
    
    doc.setFontSize(16);
    doc.text("Fighter Statistics", 10, 68);
    
    const p1 = report.fighter_stats.p1;
    const p2 = report.fighter_stats.p2;
    
    doc.setFontSize(11);
    doc.text(`PLAYER 1: ${p1.name} (${p1.provider})`, 10, 78);
    doc.text(`- Final HP: ${p1.final_hp}/100`, 15, 86);
    doc.text(`- Damage Dealt: ${p1.damage_dealt}`, 15, 94);
    doc.text(`- Prediction Accuracy: ${p1.prediction_accuracy}%`, 15, 102);
    doc.text(`- Avg Latency: ${p1.avg_response_time}s`, 15, 110);
    doc.text(`- Strategic Score: ${p1.strategic_score}`, 15, 118);
    doc.text(`- Strategies: ${p1.strategies.join(', ')}`, 15, 126);
    
    doc.text(`PLAYER 2: ${p2.name} (${p2.provider})`, 110, 78);
    doc.text(`- Final HP: ${p2.final_hp}/100`, 115, 86);
    doc.text(`- Damage Dealt: ${p2.damage_dealt}`, 115, 94);
    doc.text(`- Prediction Accuracy: ${p2.prediction_accuracy}%`, 115, 102);
    doc.text(`- Avg Latency: ${p2.avg_response_time}s`, 115, 110);
    doc.text(`- Strategic Score: ${p2.strategic_score}`, 115, 118);
    doc.text(`- Strategies: ${p2.strategies.join(', ')}`, 115, 126);

    doc.setFontSize(14);
    doc.text("Victory Analysis", 10, 142);
    doc.setFontSize(11);
    const reasonsStr = report.victory_analysis.reasons.join(', ');
    const splitReasons = doc.splitTextToSize(`Factors: ${reasonsStr}`, 180);
    doc.text(splitReasons, 10, 150);
    
    doc.addPage();
    doc.setFontSize(16);
    doc.text("Turn-By-Turn AI Reasoning Breakdown", 10, 20);
    
    doc.setFontSize(9);
    let y = 30;
    
    report.turn_by_turn.forEach(turn => {
        if (y > 250) {
            doc.addPage();
            y = 20;
        }
        
        doc.setFontSize(11);
        doc.setFont(undefined, 'bold');
        doc.setTextColor(50, 50, 50);
        doc.text(`Turn ${turn.turn} - First to act: ${turn.first_mover.toUpperCase()}`, 10, y);
        doc.setFont(undefined, 'normal');
        doc.setTextColor(0, 0, 0);
        y += 6;
        
        doc.setFontSize(9);
        
        // P1
        doc.setFont(undefined, 'bold');
        doc.text(`Player 1 (${p1.name}) Action: ${turn.p1_action} | Target Prediction: ${turn.p1_prediction || 'N/A'}`, 10, y);
        y += 5;
        doc.setFont(undefined, 'normal');
        const p1ThinkLines = doc.splitTextToSize(`Reasoning: ${turn.p1_thinking}`, 190);
        doc.text(p1ThinkLines, 10, y);
        y += p1ThinkLines.length * 4 + 2;

        // P2
        doc.setFont(undefined, 'bold');
        doc.text(`Player 2 (${p2.name}) Action: ${turn.p2_action} | Target Prediction: ${turn.p2_prediction || 'N/A'}`, 10, y);
        y += 5;
        doc.setFont(undefined, 'normal');
        const p2ThinkLines = doc.splitTextToSize(`Reasoning: ${turn.p2_thinking}`, 190);
        doc.text(p2ThinkLines, 10, y);
        y += p2ThinkLines.length * 4 + 2;

        // Resolution Details
        doc.setFont(undefined, 'bold');
        doc.text(`Resolution (P1 dealt ${turn.p1_damage} dmg | P2 dealt ${turn.p2_damage} dmg):`, 10, y);
        y += 5;
        doc.setFont(undefined, 'normal');
        if (turn.events && turn.events.length > 0) {
            turn.events.forEach(evt => {
                const lines = doc.splitTextToSize(`  - ${evt}`, 185);
                doc.text(lines, 15, y);
                y += lines.length * 4;
            });
        }
        y += 8;
    });
    
    doc.save(`LLM-Fight-Report-${Date.now()}.pdf`);
};
