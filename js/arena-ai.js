/**
 * AI arena client — clean flat structure, no nested initSocket wrapper.
 */

// ─── URL params ─────────────────────────────────────────────────────────────
const urlParams = new URLSearchParams(window.location.search);
const p1Selection = urlParams.get('p1') || '1';
const p2Selection = urlParams.get('p2') || '2';
const p1CustomName = urlParams.get('p1name') || '';
const p2CustomName = urlParams.get('p2name') || '';

let fightTopic = '';
let socket = null;

window.escHtml = function (unsafe) {
    if (!unsafe) return "";
    return unsafe.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
};

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

    function showThinking(logElement, playerNum) {
        if (logElement.querySelector('.thinking-indicator')) {
            return;
        }
        const element = document.createElement('div');
        element.className = 'thinking-indicator';
        element.textContent = 'Thinking...';
        logElement.prepend(element);

        // AI Aura logic
        const fighterWrapper = document.getElementById(`fighter${playerNum}-wrapper`);
        if (fighterWrapper) fighterWrapper.classList.add('ai-thinking');
    }

    function hideThinking(logElement, playerNum) {
        const element = logElement.querySelector('.thinking-indicator');
        if (element) {
            element.remove();
        }

        const fighterWrapper = document.getElementById(`fighter${playerNum}-wrapper`);
        if (fighterWrapper) fighterWrapper.classList.remove('ai-thinking');
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

    // Combo storage
    let p1Combo = 0;
    let p2Combo = 0;

    function triggerHitEffects(events, data) {
        let delay = 180;

        // reset combos if no hits land
        let p1HitLanded = false;
        let p2HitLanded = false;

        (events || []).forEach((event) => {
            const isTargetP1 = event.target === data.p1.name;
            const targetWrapper = isTargetP1 ? fighter1Wrapper : fighter2Wrapper;
            const targetFighter = isTargetP1 ? fighter1 : fighter2;
            const attackerWrapper = isTargetP1 ? fighter2Wrapper : fighter1Wrapper;

            if (event.type === 'hit') {
                if (isTargetP1) p2HitLanded = true;
                else p1HitLanded = true;
            }

            setTimeout(() => {
                if (event.type === 'hit') {
                    showHitEffect(targetWrapper);
                    targetFighter.classList.add('hit');
                    setTimeout(() => targetFighter.classList.remove('hit'), 300);

                    const match = event.text.match(/for (\d+) damage/);
                    const damage = match ? parseInt(match[1], 10) : 0;

                    // Track Combos
                    const hitByP1 = !isTargetP1;
                    if (hitByP1) {
                        p1Combo++;
                        p2Combo = 0;
                    } else {
                        p2Combo++;
                        p1Combo = 0;
                    }
                    const activeCombo = hitByP1 ? p1Combo : p2Combo;
                    if (activeCombo >= 2) {
                        setTimeout(() => showFloatingText(attackerWrapper, `COMBO x${activeCombo}!`, 'combo'), 100);
                    }

                    if (damage >= 40) {
                        playSound('hit-sound');
                        showFloatingText(attackerWrapper, 'ULTIMATE MOVE!', 'ultimate');
                        setTimeout(() => showFloatingText(targetWrapper, `-${damage}`, 'damage massive'), 400);
                        triggerArenaShake('massive');
                        const arena = document.querySelector('.fight-arena');
                        if (arena) {
                            arena.classList.add('flash-critical');
                            setTimeout(() => arena.classList.remove('flash-critical'), 500);
                        }
                        const hpBarId = isTargetP1 ? 'p1-health' : 'p2-health';
                        const hpBarParent = document.getElementById(hpBarId)?.parentElement;
                        if (hpBarParent) {
                            hpBarParent.classList.add("critical-hit");
                            setTimeout(() => hpBarParent.classList.remove("critical-hit"), 400);
                        }
                    } else if (damage >= 20) {
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

                        const hpBarId = isTargetP1 ? 'p1-health' : 'p2-health';
                        const hpBarParent = document.getElementById(hpBarId)?.parentElement;
                        if (hpBarParent) {
                            hpBarParent.classList.add("critical-hit");
                            setTimeout(() => hpBarParent.classList.remove("critical-hit"), 400);
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

        if (!p1HitLanded) p1Combo = 0;
        if (!p2HitLanded) p2Combo = 0;
    }

    const socketBaseUrl = window.location.origin.startsWith('http')
        ? window.location.origin
        : 'http://localhost:5000';

    let fightStarted = false;
    window.matchTimeline = [];
    window.visualReplayInterval = null;
    window.matchStartData = null;

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
        window.matchTimeline = [];
        window.matchStartData = data;
        document.getElementById('p1-name').textContent = p1CustomName || data.p1.name;
        document.getElementById('p2-name').textContent = p2CustomName || data.p2.name;
        document.getElementById('p1-model-name').textContent = data.p1.model_id;
        document.getElementById('p2-model-name').textContent = data.p2.model_id;
        document.getElementById('p1-dot').style.background = data.p1.color;
        document.getElementById('p2-dot').style.background = data.p2.color;

        // Store custom names for use elsewhere
        window.p1DisplayName = p1CustomName || data.p1.name;
        window.p2DisplayName = p2CustomName || data.p2.name;

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
        showThinking(cotLogP1, 1);
        showThinking(cotLogP2, 2);
        turnCounter.textContent = `TURN ${data.turn}/30 THINKING`;
    });

    window.processTurnVisuals = function(data, isReplay = false) {
        hideThinking(cotLogP1, 1);
        hideThinking(cotLogP2, 2);

        if (isReplay && data.turn === 1) {
            cotLogP1.innerHTML = '';
            cotLogP2.innerHTML = '';
            eventFeed.innerHTML = '';
        }

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
            
            const r1 = data.p1.total_reward || 0;
            const r2 = data.p2.total_reward || 0;
            const p1Crown = r1 > r2 ? ' 👑' : '';
            const p2Crown = r2 > r1 ? ' 👑' : '';
            
            const getScoreColor = (score) => {
                if (score >= 200) return '#ff00ff';
                if (score >= 120) return '#ffeb3b';
                if (score >= 60) return '#1dd58f';
                if (score >= 20) return '#4af';
                return '#aab7d1';
            };

            const rl1 = document.getElementById('p1-reward');
            const rl2 = document.getElementById('p2-reward');

            if (rl1) {
                rl1.textContent = `RL Score: ${r1}${p1Crown}`;
                rl1.style.color = getScoreColor(r1);
                rl1.style.textShadow = `0 0 10px ${getScoreColor(r1)}88, 1px 1px 0 #000`;
            }
            if (rl2) {
                rl2.textContent = `${p2Crown}RL Score: ${r2}`;
                rl2.style.color = getScoreColor(r2);
                rl2.style.textShadow = `0 0 10px ${getScoreColor(r2)}88, 1px 1px 0 #000`;
            }
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
    };

    socket.on('turn_result', (data) => {
        window.matchTimeline.push(data);
        window.processTurnVisuals(data, false);
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

        // Use custom names if provided
        const winnerDisplayName = winPosition === 'left'
            ? (p1CustomName || data.winner)
            : (p2CustomName || data.winner);

        if (data.winner && data.winner !== 'DRAW') {
            const isKnockout = data.p1_final.health <= 0 || data.p2_final.health <= 0;

            setFighterClass(winnerFighter, winnerSkin, 'victory');
            setFighterClass(loserFighter, loserSkin, 'defeated');
            playSound('win-sound');
            setTimeout(() => playSound('thud-sound'), 400);
            startSparkles(winnerWrapper);

            if (isKnockout) {
                setTimeout(() => {
                    const koText = document.createElement('div');
                    koText.className = 'knockout-text';
                    koText.textContent = 'KNOCKOUT!';
                    // Put it directly inside the victory overlay so it z-indexes correctly
                    victoryOverlay.prepend(koText);
                }, 500);
                triggerArenaShake('massive');
            }

            setTimeout(async () => {
                stopSparkles();
                winnerText.textContent = `${winnerDisplayName} WINS!`;
                winnerModel.textContent = isKnockout ? `by Devastating Knockout` : `in ${data.turns} turns`;

                try {
                    const res = await fetch(`${socketBaseUrl}/api/download_report/${socket.id}`);
                    const reportData = await res.json();
                    if (reportData.analysis_report) {
                        const report = reportData.analysis_report;
                        window.fightReport = report;
                        const p1Stats = report.fighter_stats.p1;
                        const p2Stats = report.fighter_stats.p2;

                        // Use custom names for stats display
                        const p1Label = p1CustomName || 'P1';
                        const p2Label = p2CustomName || 'P2';

                        const heatmapHtml = [];
                        if (p1Stats.strategy_heatmap) heatmapHtml.push(`<img src="${p1Stats.strategy_heatmap}" class="heatmap-img" />`);
                        if (p2Stats.strategy_heatmap) heatmapHtml.push(`<img src="${p2Stats.strategy_heatmap}" class="heatmap-img" />`);
                        document.getElementById('heatmap-container').innerHTML = heatmapHtml.join('');

                        // Helper to safely extract nested metric values
                        function mv(obj, ...keys) {
                            let v = obj;
                            for (const k of keys) { if (v == null) return 'N/A'; v = v[k]; }
                            return v != null ? v : 'N/A';
                        }

                        const bm1 = p1Stats.benchmark_metrics || {};
                        const bm2 = p2Stats.benchmark_metrics || {};

                        statsGrid.innerHTML = `
                        <style>
                        .decision-board { display:flex; flex-direction:column; gap:25px; width:100%; margin:30px 0; }
                        .db-cat { background:rgba(10,15,30,0.8); border:1px solid rgba(0,240,255,0.4); border-radius:12px; padding:25px; box-shadow:0 8px 32px rgba(0,200,255,0.15); }
                        .db-title { color:#00f0ff; text-align:center; font-size:16px; margin-bottom:20px; letter-spacing:2px; border-bottom:1px solid rgba(0,240,255,0.2); padding-bottom:10px; text-shadow:0 0 10px rgba(0,240,255,0.4); }
                        .db-row { display:flex; gap:25px; }
                        .db-col { flex:1; display:flex; flex-direction:column; gap:12px; }
                        .db-col.p1 { border-right:1px dashed rgba(255,255,255,0.1); padding-right:20px; }
                        .db-col.p2 { padding-left:20px; }
                        .db-stat { background:linear-gradient(90deg, rgba(0,255,149,0.05), transparent); padding:16px; border-left:3px solid #00f0ff; position:relative; border-radius:0 4px 4px 0; }
                        .db-col.p2 .db-stat { background:linear-gradient(270deg, rgba(255,122,69,0.05), transparent); border-left:none; border-right:3px solid #ff7a45; text-align:right; border-radius:4px 0 0 4px; }
                        .db-label { font-size:10px; color:#8fa0be; margin-bottom:8px; text-transform:uppercase; letter-spacing:1px; }
                        .db-val { font-size:20px; font-weight:bold; color:#fff; text-shadow:0 0 8px rgba(255,255,255,0.3); }
                        .db-val.danger { color: #ff3366; text-shadow: 0 0 10px rgba(255,51,102,0.5); }
                        .db-meta { font-size:8px; color:#ffd57c; margin-top:6px; }
                        .db-sub { font-size:7px; color:#6a748a; display:block; margin-top:4px; text-transform:none; letter-spacing:0; }
                        .victory-text-analysis { font-size:14px; color:#b0c4de; text-align:center; line-height:1.8; padding: 15px; background: rgba(0,0,0,0.2); border-radius: 8px;}
                        </style>
                        <div class="decision-board">
                           <!-- CAT 1: CORE INTELLIGENCE -->
                           <div class="db-cat">
                              <div class="db-title">⚡ CORE INTELLIGENCE & PERFORMANCE</div>
                              <div class="db-row">
                                 <div class="db-col p1">
                                    <h3 style="color:#00f0ff; text-align:center; font-size:12px; margin-bottom:10px;">${p1Label}</h3>
                                    <div class="db-stat"><div class="db-label">Intel Score</div><div class="db-val">${p1Stats.intelligence_score || 0}</div></div>
                                    <div class="db-stat"><div class="db-label">Reasoning Quality</div><div class="db-val">${p1Stats.reasoning_quality}/4</div></div>
                                    <div class="db-stat"><div class="db-label">RL Reward</div><div class="db-val">${p1Stats.total_reward}</div></div>
                                    <div class="db-stat"><div class="db-label">Argument Depth<span class="db-sub">Clean: ${mv(bm1,'argument_depth','low_stress_avg')} → Stressed: ${mv(bm1,'argument_depth','high_stress_avg')}</span></div><div class="db-val">${mv(bm1,'argument_depth','avg')}/10</div></div>
                                 </div>
                                 <div class="db-col p2">
                                    <h3 style="color:#ff7a45; text-align:center; font-size:12px; margin-bottom:10px;">${p2Label}</h3>
                                    <div class="db-stat"><div class="db-label">Intel Score</div><div class="db-val">${p2Stats.intelligence_score || 0}</div></div>
                                    <div class="db-stat"><div class="db-label">Reasoning Quality</div><div class="db-val">${p2Stats.reasoning_quality}/4</div></div>
                                    <div class="db-stat"><div class="db-label">RL Reward</div><div class="db-val">${p2Stats.total_reward}</div></div>
                                    <div class="db-stat"><div class="db-label">Argument Depth<span class="db-sub">Clean: ${mv(bm2,'argument_depth','low_stress_avg')} → Stressed: ${mv(bm2,'argument_depth','high_stress_avg')}</span></div><div class="db-val">${mv(bm2,'argument_depth','avg')}/10</div></div>
                                 </div>
                              </div>
                           </div>

                           <!-- CAT 2: RELIABILITY -->
                           <div class="db-cat">
                              <div class="db-title">🎯 RELIABILITY & ACCURACY</div>
                              <div class="db-row">
                                 <div class="db-col p1">
                                    <div class="db-stat"><div class="db-label">Prediction Accuracy</div><div class="db-val">${p1Stats.prediction_accuracy}%</div></div>
                                    <div class="db-stat"><div class="db-label">Thinking Consistency</div><div class="db-val">${p1Stats.thinking_consistency}%</div></div>
                                    <div class="db-stat"><div class="db-label">Action-Reason Alignment</div><div class="db-val">${mv(bm1,'action_alignment')}/100</div></div>
                                 </div>
                                 <div class="db-col p2">
                                    <div class="db-stat"><div class="db-label">Prediction Accuracy</div><div class="db-val">${p2Stats.prediction_accuracy}%</div></div>
                                    <div class="db-stat"><div class="db-label">Thinking Consistency</div><div class="db-val">${p2Stats.thinking_consistency}%</div></div>
                                    <div class="db-stat"><div class="db-label">Action-Reason Alignment</div><div class="db-val">${mv(bm2,'action_alignment')}/100</div></div>
                                 </div>
                              </div>
                           </div>

                           <!-- CAT 3: ROBUSTNESS -->
                           <div class="db-cat">
                              <div class="db-title">🛡️ STRESS ROBUSTNESS</div>
                              <div class="db-row">
                                 <div class="db-col p1">
                                    <div class="db-stat"><div class="db-label">Hallucination Score<span class="db-sub">Penalty: -${mv(bm1,'hallucination','raw_penalty')}pt | Rates: ${mv(bm1,'hallucination','low_stress_hallu_rate')}%→${mv(bm1,'hallucination','high_stress_hallu_rate')}%</span></div><div class="db-val ${mv(bm1,'hallucination','truth_score') < 70 ? 'danger' : ''}">${mv(bm1,'hallucination','truth_score')}/100</div></div>
                                    <div class="db-stat"><div class="db-label">Self-Contradiction</div><div class="db-val">${mv(bm1,'self_contradiction','count')}</div><div class="db-meta">events</div></div>
                                    <div class="db-stat"><div class="db-label">Stress Resilience<span class="db-sub">Param drift from baseline</span></div><div class="db-val">${mv(bm1,'stress_resilience','score')}/100</div></div>
                                    <div class="db-stat"><div class="db-label">Reasoning Faithfulness<span class="db-sub">${mv(bm1,'deception_score','label')}</span></div><div class="db-val">${mv(bm1,'deception_score','score')}/100</div></div>
                                 </div>
                                 <div class="db-col p2">
                                    <div class="db-stat"><div class="db-label">Hallucination Score<span class="db-sub">Penalty: -${mv(bm2,'hallucination','raw_penalty')}pt | Rates: ${mv(bm2,'hallucination','low_stress_hallu_rate')}%→${mv(bm2,'hallucination','high_stress_hallu_rate')}%</span></div><div class="db-val ${mv(bm2,'hallucination','truth_score') < 70 ? 'danger' : ''}">${mv(bm2,'hallucination','truth_score')}/100</div></div>
                                    <div class="db-stat"><div class="db-label">Self-Contradiction</div><div class="db-val">${mv(bm2,'self_contradiction','count')}</div><div class="db-meta">events</div></div>
                                    <div class="db-stat"><div class="db-label">Stress Resilience<span class="db-sub">Param drift from baseline</span></div><div class="db-val">${mv(bm2,'stress_resilience','score')}/100</div></div>
                                    <div class="db-stat"><div class="db-label">Reasoning Faithfulness<span class="db-sub">${mv(bm2,'deception_score','label')}</span></div><div class="db-val">${mv(bm2,'deception_score','score')}/100</div></div>
                                 </div>
                              </div>
                           </div>

                           <!-- CAT 4: TACTICS & ADAPTATION -->
                           <div class="db-cat">
                              <div class="db-title">⚔️ TACTICS & COGNITION</div>
                              <div class="db-row">
                                 <div class="db-col p1">
                                    <div class="db-stat"><div class="db-label">Tactical Efficiency<span class="db-sub">Early: ${mv(bm1,'tactical_efficiency','early_turns_efficiency')}% → Late: ${mv(bm1,'tactical_efficiency','late_turns_efficiency')}%</span></div><div class="db-val">${mv(bm1,'tactical_efficiency','efficiency')}%</div></div>
                                    <div class="db-stat"><div class="db-label">Strategy Diversity</div><div class="db-val">${mv(bm1,'strategy_diversity')}%</div></div>
                                    <div class="db-stat"><div class="db-label">Repetition Rate<span class="db-sub">Clean: ${mv(bm1,'repetition_rate','low_stress_rate')}% → Stressed: ${mv(bm1,'repetition_rate','high_stress_rate')}%</span></div><div class="db-val">${mv(bm1,'repetition_rate','rate')}%</div></div>
                                    <div class="db-stat"><div class="db-label">Pattern Detection</div><div class="db-val">${mv(bm1,'pattern_detection','detection_rate')}%</div><div class="db-meta">${mv(bm1,'pattern_detection','count')}/${mv(bm1,'pattern_detection','opportunities')} streaks</div></div>
                                    <div class="db-stat"><div class="db-label">Self-Correction</div><div class="db-val">${mv(bm1,'self_correction','correction_rate')}%</div><div class="db-meta">${mv(bm1,'self_correction','count')} times</div></div>
                                    <div class="db-stat"><div class="db-label">Logical Structure<span class="db-sub">Clean: ${mv(bm1,'logical_structure','low_stress_avg')} → Stressed: ${mv(bm1,'logical_structure','high_stress_avg')}</span></div><div class="db-val">${mv(bm1,'logical_structure','avg')}/10</div></div>
                                 </div>
                                 <div class="db-col p2">
                                    <div class="db-stat"><div class="db-label">Tactical Efficiency<span class="db-sub">Early: ${mv(bm2,'tactical_efficiency','early_turns_efficiency')}% → Late: ${mv(bm2,'tactical_efficiency','late_turns_efficiency')}%</span></div><div class="db-val">${mv(bm2,'tactical_efficiency','efficiency')}%</div></div>
                                    <div class="db-stat"><div class="db-label">Strategy Diversity</div><div class="db-val">${mv(bm2,'strategy_diversity')}%</div></div>
                                    <div class="db-stat"><div class="db-label">Repetition Rate<span class="db-sub">Clean: ${mv(bm2,'repetition_rate','low_stress_rate')}% → Stressed: ${mv(bm2,'repetition_rate','high_stress_rate')}%</span></div><div class="db-val">${mv(bm2,'repetition_rate','rate')}%</div></div>
                                    <div class="db-stat"><div class="db-label">Pattern Detection</div><div class="db-val">${mv(bm2,'pattern_detection','detection_rate')}%</div><div class="db-meta">${mv(bm2,'pattern_detection','count')}/${mv(bm2,'pattern_detection','opportunities')} streaks</div></div>
                                    <div class="db-stat"><div class="db-label">Self-Correction</div><div class="db-val">${mv(bm2,'self_correction','correction_rate')}%</div><div class="db-meta">${mv(bm2,'self_correction','count')} times</div></div>
                                    <div class="db-stat"><div class="db-label">Logical Structure<span class="db-sub">Clean: ${mv(bm2,'logical_structure','low_stress_avg')} → Stressed: ${mv(bm2,'logical_structure','high_stress_avg')}</span></div><div class="db-val">${mv(bm2,'logical_structure','avg')}/10</div></div>
                                 </div>
                              </div>
                           </div>
                           
                           <div class="db-cat">
                              <div class="db-title">🏅 VICTORY ANALYSIS</div>
                              <div class="db-row">
                                 <div class="db-col p1" style="border:none; padding:10px; width:100%;">
                                    <div class="victory-text-analysis">${report.victory_analysis.reasons.join(' · ')}</div>
                                 </div>
                              </div>
                           </div>
                        </div>
                        `;

                        const pdfBtn = document.getElementById('download-pdf-btn');
                        if (pdfBtn) pdfBtn.style.display = 'inline-block';
                    }
                } catch (err) {
                    console.error("Failed to fetch post-match report", err);
                    const p1Label = p1CustomName || 'P1';
                    const p2Label = p2CustomName || 'P2';
                    statsGrid.innerHTML = `
                    <div class="stat-card"><div class="stat-label">${p1Label} Damage</div><div class="stat-val">${data.p1_final.total_damage_dealt}</div></div>
                    <div class="stat-card"><div class="stat-label">${p2Label} Damage</div><div class="stat-val">${data.p2_final.total_damage_dealt}</div></div>
                    <div class="stat-card"><div class="stat-label">${p1Label} Avg Latency</div><div class="stat-val">${data.p1_final.avg_response_time}s</div></div>
                    <div class="stat-card"><div class="stat-label">${p2Label} Avg Latency</div><div class="stat-val">${data.p2_final.avg_response_time}s</div></div>
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

window.downloadPDFReport = function () {
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
    let docY = 30;
    doc.text(`Date: ${new Date(report.match_info.date).toLocaleString()}`, 10, docY);
    docY += 8;

    if (report.match_info.topic) {
        const topicLines = doc.splitTextToSize(`Topic: ${report.match_info.topic}`, 180);
        doc.text(topicLines, 10, docY);
        docY += topicLines.length * 6;
    }

    doc.text(`Winner: ${report.match_info.winner}`, 10, docY);
    docY += 8;
    doc.text(`Victory Type: ${report.match_info.victory_type}`, 10, docY);
    docY += 8;
    doc.text(`Total Turns: ${report.match_info.total_turns}`, 10, docY);
    docY += 14;

    doc.setFontSize(16);
    doc.text("Fighter Statistics", 10, docY);
    docY += 10;

    const p1 = report.fighter_stats.p1;
    const p2 = report.fighter_stats.p2;

    doc.setFontSize(11);
    doc.text(`PLAYER 1: ${p1.name} (${p1.provider})`, 10, docY);
    doc.text(`PLAYER 2: ${p2.name} (${p2.provider})`, 105, docY);
    docY += 8;
    doc.text(`- Final HP: ${p1.final_hp}/100`, 15, docY);
    doc.text(`- Final HP: ${p2.final_hp}/100`, 110, docY);
    docY += 8;
    doc.text(`- Damage Dealt: ${p1.damage_dealt}`, 15, docY);
    doc.text(`- Damage Dealt: ${p2.damage_dealt}`, 110, docY);
    docY += 8;
    doc.text(`- Prediction Accuracy: ${p1.prediction_accuracy}%`, 15, docY);
    doc.text(`- Prediction Accuracy: ${p2.prediction_accuracy}%`, 110, docY);
    docY += 8;
    doc.text(`- Reasoning Quality: ${p1.reasoning_quality} / 4.0`, 15, docY);
    doc.text(`- Reasoning Quality: ${p2.reasoning_quality} / 4.0`, 110, docY);
    docY += 8;
    doc.text(`- Thinking Consistency: ${p1.thinking_consistency}%`, 15, docY);
    doc.text(`- Thinking Consistency: ${p2.thinking_consistency}%`, 110, docY);
    docY += 8;
    doc.text(`- Avg Latency: ${p1.avg_response_time}s`, 15, docY);
    doc.text(`- Avg Latency: ${p2.avg_response_time}s`, 110, docY);
    docY += 8;
    doc.text(`- RL Total Reward: ${p1.total_reward}`, 15, docY);
    doc.text(`- RL Total Reward: ${p2.total_reward}`, 110, docY);
    docY += 8;
    doc.text(`- Intelligence Score: ${p1.intelligence_score}`, 15, docY);
    doc.text(`- Intelligence Score: ${p2.intelligence_score}`, 110, docY);
    docY += 8;

    const bm1 = p1.benchmark_metrics || {};
    const bm2 = p2.benchmark_metrics || {};

    doc.setFontSize(9);
    doc.text(`- Strategy Diversity: ${bm1.strategy_diversity || 0}%`, 15, docY);
    doc.text(`- Strategy Diversity: ${bm2.strategy_diversity || 0}%`, 110, docY);
    docY += 6;
    doc.text(`- Tactical Efficiency: ${(bm1.tactical_efficiency || {}).efficiency || 0}%`, 15, docY);
    doc.text(`- Tactical Efficiency: ${(bm2.tactical_efficiency || {}).efficiency || 0}%`, 110, docY);
    docY += 6;
    doc.text(`- Stance Consistency: ${(bm1.stance_consistency || {}).score || 0}%`, 15, docY);
    doc.text(`- Stance Consistency: ${(bm2.stance_consistency || {}).score || 0}%`, 110, docY);
    docY += 6;
    doc.text(`- Repetition Rate: ${(bm1.repetition_rate || {}).overall || 0}%`, 15, docY);
    doc.text(`- Repetition Rate: ${(bm2.repetition_rate || {}).overall || 0}%`, 110, docY);
    docY += 6;
    doc.text(`- Self-Correction: ${(bm1.self_correction || {}).correction_rate || 0}%`, 15, docY);
    doc.text(`- Self-Correction: ${(bm2.self_correction || {}).correction_rate || 0}%`, 110, docY);
    docY += 6;
    doc.text(`- Stress Resilience: ${(bm1.stress_resilience || {}).resilience_score || 0}/100`, 15, docY);
    doc.text(`- Stress Resilience: ${(bm2.stress_resilience || {}).resilience_score || 0}/100`, 110, docY);
    docY += 6;
    doc.text(`- Pattern Detection: ${(bm1.pattern_detection || {}).detection_rate || 0}%`, 15, docY);
    doc.text(`- Pattern Detection: ${(bm2.pattern_detection || {}).detection_rate || 0}%`, 110, docY);
    docY += 6;
    doc.text(`- Argument Depth: ${bm1.argument_depth || 0}/10`, 15, docY);
    doc.text(`- Argument Depth: ${bm2.argument_depth || 0}/10`, 110, docY);
    docY += 6;
    doc.text(`- Logical Structure: ${(bm1.logical_structure || {}).avg || 0}/10`, 15, docY);
    doc.text(`- Logical Structure: ${(bm2.logical_structure || {}).avg || 0}/10`, 110, docY);
    docY += 6;
    doc.text(`- Deception Events: ${(bm1.deception_score || {}).count || 0}`, 15, docY);
    doc.text(`- Deception Events: ${(bm2.deception_score || {}).count || 0}`, 110, docY);
    docY += 6;
    doc.text(`- Hallucination Penalty: ${(bm1.hallucination || {}).raw_penalty || 0}`, 15, docY);
    doc.text(`- Hallucination Penalty: ${(bm2.hallucination || {}).raw_penalty || 0}`, 110, docY);
    docY += 16;

    if (docY > 260) {
        doc.addPage();
        docY = 20;
    }

    doc.setFontSize(14);
    doc.text("Executive Summary & Victory Analysis", 10, docY);
    docY += 8;
    doc.setFontSize(11);
    const summaryStr = `The match concluded with a ${report.match_info.victory_type} by ${report.match_info.winner}. Core factors heavily skewing the outcome included: ${report.victory_analysis.reasons.join(', ')}. The model optimization was driven effectively by the RL feedback loop, pushing final respective intelligence scores to P1: ${p1.intelligence_score} and P2: ${p2.intelligence_score}.`;
    const splitSummary = doc.splitTextToSize(summaryStr, 180);
    doc.text(splitSummary, 10, docY);
    docY += splitSummary.length * 6 + 6;

    doc.setFontSize(14);
    doc.text("Understanding the Metrics & Benchmarks", 10, docY);
    docY += 8;
    doc.setFontSize(10);
    doc.setTextColor(60, 60, 60);
    const rulesStr = `The LLM Fight Club benchmarks evaluate core reasoning categories (Technical, Ethical, Scientific, Business, Creative) against real adversarial parameter stress. 
- PUNCH (10 dmg): Increases opponent temperature (+0.3). Dodged by DUCK.
- KICK (15 dmg): Squashes opponent top_p (-0.3). Cannot be dodged.
- DEFEND: Blocks attacks but damages own top_p.
- DUCK: Dodges punches but degrades own presence_penalty.
- MOVE_FORWARD/BACKWARD: Manipulates distance and degrades max_tokens/frequency_penalty.
Models must maintain logic, avoid hallucination, and debate effectively while protecting their system parameters under active degradation.`;
    const splitRules = doc.splitTextToSize(rulesStr, 180);
    doc.text(splitRules, 10, docY);
    doc.setTextColor(0, 0, 0);

    // Heatmaps
    doc.addPage();
    doc.setFontSize(16);
    doc.text("Strategic Heatmaps (Movement & Attack Patterns)", 10, 20);
    doc.setFontSize(11);

    let hmY = 30;
    if (p1.strategy_heatmap) {
        doc.text(`Player 1 (${p1.name}) Pattern Adoption`, 10, hmY);
        doc.addImage(p1.strategy_heatmap, 'PNG', 10, hmY + 5, 180, 45);
        hmY += 65;
    }

    if (p2.strategy_heatmap) {
        doc.text(`Player 2 (${p2.name}) Pattern Adoption`, 10, hmY);
        doc.addImage(p2.strategy_heatmap, 'PNG', 10, hmY + 5, 180, 45);
    }

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
        doc.text(`Player 1 (${p1.name}) Action: ${turn.p1_action}`, 10, y);
        y += 5;
        doc.setFontSize(8);
        doc.setTextColor(100, 100, 100);
        const p1Params = turn.p1_params_before || {};
        const p1ParamsA = turn.p1_params_after || {};
        doc.text(`Params Before: temp=${p1Params.temperature || 0.7} | top_p=${p1Params.top_p || 1.0} | freq=${p1Params.frequency_penalty || 0} | pres=${p1Params.presence_penalty || 0}`, 15, y);
        y += 4;
        doc.text(`Params After: temp=${p1ParamsA.temperature || 0.7} | top_p=${p1ParamsA.top_p || 1.0} | freq=${p1ParamsA.frequency_penalty || 0} | pres=${p1ParamsA.presence_penalty || 0}`, 15, y);
        y += 5;
        doc.setFontSize(9);
        doc.setTextColor(0, 0, 0);

        doc.setFont(undefined, 'normal');
        doc.setTextColor(0, 100, 0); // dark green
        if (turn.p1_reward_reasons && turn.p1_reward_reasons.length > 0) {
            const r1 = doc.splitTextToSize(`Optimized For: ${turn.p1_reward_reasons.join(', ')}`, 190);
            doc.text(r1, 10, y);
            y += r1.length * 4 + 2;
        }
        doc.setTextColor(0, 0, 0);
        const p1ThinkLines = doc.splitTextToSize(`Reasoning Base: ${turn.p1_thinking}`, 190);
        doc.text(p1ThinkLines, 10, y);
        y += p1ThinkLines.length * 4 + 2;

        // P2
        doc.setFont(undefined, 'bold');
        doc.text(`Player 2 (${p2.name}) Action: ${turn.p2_action}`, 10, y);
        y += 5;
        doc.setFontSize(8);
        doc.setTextColor(100, 100, 100);
        const p2Params = turn.p2_params_before || {};
        const p2ParamsA = turn.p2_params_after || {};
        doc.text(`Params Before: temp=${p2Params.temperature || 0.7} | top_p=${p2Params.top_p || 1.0} | freq=${p2Params.frequency_penalty || 0} | pres=${p2Params.presence_penalty || 0}`, 15, y);
        y += 4;
        doc.text(`Params After: temp=${p2ParamsA.temperature || 0.7} | top_p=${p2ParamsA.top_p || 1.0} | freq=${p2ParamsA.frequency_penalty || 0} | pres=${p2ParamsA.presence_penalty || 0}`, 15, y);
        y += 5;
        doc.setFontSize(9);
        doc.setTextColor(0, 0, 0);

        doc.setFont(undefined, 'normal');
        doc.setTextColor(0, 100, 0);
        if (turn.p2_reward_reasons && turn.p2_reward_reasons.length > 0) {
            const r2 = doc.splitTextToSize(`Optimized For: ${turn.p2_reward_reasons.join(', ')}`, 190);
            doc.text(r2, 10, y);
            y += r2.length * 4 + 2;
        }
        doc.setTextColor(0, 0, 0);
        const p2ThinkLines = doc.splitTextToSize(`Reasoning Base: ${turn.p2_thinking}`, 190);
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
        y += 10;
    });

    doc.save(`LLM-Fight-Report-${Date.now()}.pdf`);
};

window.showReplay = function () {
    if (!window.fightReport) return;

    const timelineEl = document.getElementById('replay-timeline');
    timelineEl.innerHTML = '';

    window.fightReport.turn_by_turn.forEach(turn => {
        const item = document.createElement('div');
        item.className = 'replay-timeline-item';

        const eventsHtml = turn.events.map(e => `<div>${e}</div>`).join('');

        item.innerHTML = `
            <div class="replay-turn">Turn ${turn.turn} ─ ${turn.p1_action} vs ${turn.p2_action}</div>
            <div style="color: #4af; margin-bottom: 5px;">P1 (Dmg: ${turn.p1_damage}) Thinking: "${window.escHtml ? window.escHtml(turn.p1_thinking) : turn.p1_thinking}"</div>
            <div style="color: #ff4; margin-bottom: 5px;">P2 (Dmg: ${turn.p2_damage}) Thinking: "${window.escHtml ? window.escHtml(turn.p2_thinking) : turn.p2_thinking}"</div>
            <div style="font-size: 0.85em; color: #aaa; margin-top: 8px;">
                <strong>Damage Events:</strong><br/>
                ${eventsHtml}
            </div>
        `;
        timelineEl.appendChild(item);
    });

    document.getElementById('replay-overlay').style.display = 'flex';
};

window.startVisualReplay = function(speedMap) {
    if (!window.matchTimeline || window.matchTimeline.length === 0) {
        alert("No match history found to replay!");
        return;
    }
    
    // speed is 1, 2, or 3. Default to 1 (1x)
    const speed = speedMap || 1;
    // normal interval is slightly longer than the animations ~3s.
    const intervalTime = 3000 / speed;

    document.getElementById('victory-overlay').style.display = 'none';
    document.getElementById('end-replay-btn').style.display = 'block';

    // Reset UI visually 
    if (window.matchStartData) {
        document.getElementById('p1-health').style.width = '100%';
        document.getElementById('p2-health').style.width = '100%';
        const sw1 = document.getElementById('fighter1-wrapper');
        const sw2 = document.getElementById('fighter2-wrapper');
        if (sw1) sw1.style.left = 'calc(50% - 160px)';
        if (sw2) sw2.style.left = 'calc(50% + 60px)';
        const evtFeed = document.getElementById('event-feed');
        if (evtFeed) evtFeed.innerHTML = '';
        const cl1 = document.getElementById('cot-log-p1');
        const cl2 = document.getElementById('cot-log-p2');
        if (cl1) cl1.innerHTML = '';
        if (cl2) cl2.innerHTML = '';
    }

    if (window.visualReplayInterval) clearInterval(window.visualReplayInterval);
    
    let index = 0;
    document.getElementById('end-replay-btn').innerHTML = `STOP REPLAY (0%)`;
    
    window.visualReplayInterval = setInterval(() => {
        if (index >= window.matchTimeline.length) {
            clearInterval(window.visualReplayInterval);
            document.getElementById('end-replay-btn').innerHTML = 'REPLAY FINISHED (BACK)';
            return;
        }
        
        const pct = Math.floor((index / window.matchTimeline.length) * 100);
        document.getElementById('end-replay-btn').innerHTML = `STOP REPLAY (${pct}%)`;
        window.processTurnVisuals(window.matchTimeline[index], true);
        index++;
    }, intervalTime);
};

window.endVisualReplay = function() {
    if (window.visualReplayInterval) clearInterval(window.visualReplayInterval);
    document.getElementById('end-replay-btn').style.display = 'none';
    document.getElementById('victory-overlay').style.display = 'flex';
};
