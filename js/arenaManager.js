/**
 * Arena Manager Module
 * Loads players into arena and manages the fight
 */

// Timer state
let fightTimer = 99;
let timerInterval = null;

/**
 * Initialize the arena
 */
function initArena() {
    loadFighters();
    setupHealthBars();
    startTimer();
    initFighterControls();
}

/**
 * Load selected fighters into the arena
 */
function loadFighters() {
    const p1Fighter = sessionStorage.getItem('player1Fighter') || '1';
    const p2Fighter = sessionStorage.getItem('player2Fighter') || '2';
    const p1Name = sessionStorage.getItem('player1FighterName') || 'Player 1';
    const p2Name = sessionStorage.getItem('player2FighterName') || 'Player 2';

    // Inject fighters using template
    if (typeof injectFighter === 'function') {
        injectFighter('fighter1-container', p1Fighter, 1);
        injectFighter('fighter2-container', p2Fighter, 2);
    }

    // Update player names
    const p1NameEl = document.getElementById('p1-name');
    const p2NameEl = document.getElementById('p2-name');

    if (p1NameEl) p1NameEl.textContent = p1Name;
    if (p2NameEl) p2NameEl.textContent = p2Name;
}

/**
 * Setup health bars to full
 */
function setupHealthBars() {
    const p1Health = document.getElementById('p1-health');
    const p2Health = document.getElementById('p2-health');

    if (p1Health) p1Health.style.width = '100%';
    if (p2Health) p2Health.style.width = '100%';
}

/**
 * Start the fight timer
 */
function startTimer() {
    fightTimer = 99;
    updateTimerDisplay();

    timerInterval = setInterval(() => {
        fightTimer--;
        updateTimerDisplay();

        if (fightTimer <= 0) {
            timeUp();
        }
    }, 1000);
}

/**
 * Update timer display
 */
function updateTimerDisplay() {
    const timerEl = document.getElementById('timer');
    if (timerEl) {
        timerEl.textContent = fightTimer.toString().padStart(2, '0');
    }
}

/**
 * Handle time up
 */
function timeUp() {
    clearInterval(timerInterval);

    // Determine winner by health
    const p1Health = fighterStates?.player1?.health || 0;
    const p2Health = fighterStates?.player2?.health || 0;

    if (p1Health > p2Health) {
        endFight(1);
    } else if (p2Health > p1Health) {
        endFight(2);
    } else {
        // Draw - show special message
        const overlay = document.getElementById('victory-overlay');
        const winnerText = document.getElementById('winner-text');

        if (overlay && winnerText) {
            winnerText.textContent = 'DRAW!';
            overlay.style.display = 'flex';
        }
    }
}

/**
 * Stop the timer
 */
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

/**
 * Restart the arena for a rematch
 */
function restartArena() {
    stopTimer();
    resetFight();
    startTimer();

    const overlay = document.getElementById('victory-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initArena);

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initArena, restartArena };
}
