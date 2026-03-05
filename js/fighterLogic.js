/**
 * Fighter Logic Module
 * Universal boxer logic for movement, attacks, and defense
 */

// Fighter state management
const fighterStates = {
    player1: {
        x: 150,
        y: 0,
        health: 100,
        isBlocking: false,
        isPunching: false,
        isDucking: false,
        canMove: true
    },
    player2: {
        x: 450,
        y: 0,
        health: 100,
        isBlocking: false,
        isPunching: false,
        isDucking: false,
        canMove: true
    }
};

// Key bindings
const keyBindings = {
    player1: {
        left: 'KeyA',
        right: 'KeyD',
        up: 'KeyW',
        down: 'KeyS',
        punch: 'KeyF',
        block: 'KeyG'
    },
    player2: {
        left: 'ArrowLeft',
        right: 'ArrowRight',
        up: 'ArrowUp',
        down: 'ArrowDown',
        punch: 'KeyL',
        block: 'KeyK'
    }
};

// Game constants
const MOVE_SPEED = 5;
const PUNCH_DAMAGE = 10;
const PUNCH_COOLDOWN = 300;
const BLOCK_DAMAGE_REDUCTION = 0.8;

/**
 * Initialize fighter controls
 */
function initFighterControls() {
    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('keyup', handleKeyUp);
}

/**
 * Handle key down events
 * @param {KeyboardEvent} event
 */
function handleKeyDown(event) {
    const key = event.code;

    // Player 1 controls
    if (key === keyBindings.player1.left) moveFighter(1, 'left');
    if (key === keyBindings.player1.right) moveFighter(1, 'right');
    if (key === keyBindings.player1.up) moveFighter(1, 'up');
    if (key === keyBindings.player1.down) duck(1, true);
    if (key === keyBindings.player1.punch) punch(1);
    if (key === keyBindings.player1.block) block(1, true);

    // Player 2 controls
    if (key === keyBindings.player2.left) moveFighter(2, 'left');
    if (key === keyBindings.player2.right) moveFighter(2, 'right');
    if (key === keyBindings.player2.up) moveFighter(2, 'up');
    if (key === keyBindings.player2.down) duck(2, true);
    if (key === keyBindings.player2.punch) punch(2);
    if (key === keyBindings.player2.block) block(2, true);
}

/**
 * Handle key up events
 * @param {KeyboardEvent} event
 */
function handleKeyUp(event) {
    const key = event.code;

    // Player 1 releases
    if (key === keyBindings.player1.down) duck(1, false);
    if (key === keyBindings.player1.block) block(1, false);

    // Player 2 releases
    if (key === keyBindings.player2.down) duck(2, false);
    if (key === keyBindings.player2.block) block(2, false);
}

/**
 * Move a fighter
 * @param {number} player - Player number (1 or 2)
 * @param {string} direction - Direction to move
 */
function moveFighter(player, direction) {
    const state = fighterStates[`player${player}`];
    if (!state.canMove || state.isPunching) return;

    const arena = document.getElementById('fight-arena');
    const maxX = arena ? arena.offsetWidth - 120 : 600;

    switch (direction) {
        case 'left':
            state.x = Math.max(0, state.x - MOVE_SPEED);
            break;
        case 'right':
            state.x = Math.min(maxX, state.x + MOVE_SPEED);
            break;
        case 'up':
            // Jump (simple implementation)
            if (state.y === 0) {
                state.y = -50;
                setTimeout(() => { state.y = 0; updateFighterPosition(player); }, 300);
            }
            break;
    }

    updateFighterPosition(player);
}

/**
 * Update fighter position in DOM
 * @param {number} player - Player number (1 or 2)
 */
function updateFighterPosition(player) {
    const state = fighterStates[`player${player}`];
    const container = document.getElementById(`fighter${player}-container`);

    if (container) {
        container.style.left = player === 1 ? `${state.x}px` : 'auto';
        container.style.right = player === 2 ? `${state.x}px` : 'auto';
        container.style.bottom = `${50 - state.y}px`;
    }
}

/**
 * Execute punch action
 * @param {number} player - Player number (1 or 2)
 */
function punch(player) {
    const state = fighterStates[`player${player}`];
    if (state.isPunching || state.isBlocking) return;

    state.isPunching = true;

    const boxer = document.getElementById(`boxer-p${player}`);
    if (boxer) {
        boxer.classList.add('punching');
    }

    // Play punch sound
    if (typeof playSound === 'function') {
        playSound('punch');
    }

    // Check for hit
    checkHit(player);

    // Reset after cooldown
    setTimeout(() => {
        state.isPunching = false;
        if (boxer) {
            boxer.classList.remove('punching');
        }
    }, PUNCH_COOLDOWN);
}

/**
 * Toggle block state
 * @param {number} player - Player number (1 or 2)
 * @param {boolean} isBlocking - Whether blocking is active
 */
function block(player, isBlocking) {
    const state = fighterStates[`player${player}`];
    state.isBlocking = isBlocking;

    const boxer = document.getElementById(`boxer-p${player}`);
    if (boxer) {
        boxer.classList.toggle('blocking', isBlocking);
    }

    if (isBlocking && typeof playSound === 'function') {
        playSound('defend');
    }
}

/**
 * Toggle duck state
 * @param {number} player - Player number (1 or 2)
 * @param {boolean} isDucking - Whether ducking is active
 */
function duck(player, isDucking) {
    const state = fighterStates[`player${player}`];
    state.isDucking = isDucking;

    const boxer = document.getElementById(`boxer-p${player}`);
    if (boxer) {
        boxer.classList.toggle('ducking', isDucking);
    }
}

/**
 * Check if a punch hits the opponent
 * @param {number} attacker - Attacking player number
 */
function checkHit(attacker) {
    const defender = attacker === 1 ? 2 : 1;
    const attackerState = fighterStates[`player${attacker}`];
    const defenderState = fighterStates[`player${defender}`];

    // Simple distance check
    const distance = Math.abs(attackerState.x - defenderState.x);

    if (distance < 100 && !defenderState.isDucking) {
        let damage = PUNCH_DAMAGE;

        if (defenderState.isBlocking) {
            damage *= (1 - BLOCK_DAMAGE_REDUCTION);
        }

        applyDamage(defender, damage);
    }
}

/**
 * Apply damage to a fighter
 * @param {number} player - Player number (1 or 2)
 * @param {number} damage - Damage amount
 */
function applyDamage(player, damage) {
    const state = fighterStates[`player${player}`];
    state.health = Math.max(0, state.health - damage);

    // Update health bar
    updateHealthBar(player);

    // Hit effect
    const boxer = document.getElementById(`boxer-p${player}`);
    if (boxer) {
        boxer.classList.add('hit');
        setTimeout(() => boxer.classList.remove('hit'), 200);
    }

    // Check for knockout
    if (state.health <= 0) {
        endFight(player === 1 ? 2 : 1);
    }
}

/**
 * Update health bar display
 * @param {number} player - Player number (1 or 2)
 */
function updateHealthBar(player) {
    const state = fighterStates[`player${player}`];
    const healthFill = document.getElementById(`p${player}-health`);

    if (healthFill) {
        healthFill.style.width = `${state.health}%`;

        // Update color based on health
        healthFill.classList.remove('low', 'medium');
        if (state.health <= 25) {
            healthFill.classList.add('low');
        } else if (state.health <= 50) {
            healthFill.classList.add('medium');
        }
    }
}

/**
 * End the fight
 * @param {number} winner - Winning player number
 */
function endFight(winner) {
    // Disable controls
    fighterStates.player1.canMove = false;
    fighterStates.player2.canMove = false;

    // Play victory sound
    if (typeof playSound === 'function') {
        playSound('victory');
    }

    // Show victory overlay
    const overlay = document.getElementById('victory-overlay');
    const winnerText = document.getElementById('winner-text');

    if (overlay && winnerText) {
        const winnerName = sessionStorage.getItem(`player${winner}FighterName`) || `Player ${winner}`;
        winnerText.textContent = `${winnerName} WINS!`;
        overlay.style.display = 'flex';
    }
}

/**
 * Reset fighter states for a new fight
 */
function resetFight() {
    fighterStates.player1 = { x: 150, y: 0, health: 100, isBlocking: false, isPunching: false, isDucking: false, canMove: true };
    fighterStates.player2 = { x: 450, y: 0, health: 100, isBlocking: false, isPunching: false, isDucking: false, canMove: true };

    updateHealthBar(1);
    updateHealthBar(2);
    updateFighterPosition(1);
    updateFighterPosition(2);
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { initFighterControls, fighterStates, resetFight };
}
