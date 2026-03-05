/**
 * Character Selection Module
 * Handles fighter selection logic for both players
 */

// Selection state
const selectionState = {
    player1: null,
    player2: null
};

// Fighter data
const fighters = {
    1: { name: 'GPT-4', image: 'assets/images/characters/fighter1.png', color: '#00a67d' },
    2: { name: 'Claude', image: 'assets/images/characters/fighter2.png', color: '#d97706' },
    3: { name: 'Gemini', image: 'assets/images/characters/fighter3.png', color: '#4285f4' },
    4: { name: 'LLaMA', image: 'assets/images/characters/fighter4.png', color: '#7c3aed' }
};

/**
 * Initialize character selection
 */
function initCharacterSelect() {
    // Set up Player 1 grid
    const p1Grid = document.getElementById('p1-grid');
    if (p1Grid) {
        p1Grid.querySelectorAll('.character-card').forEach(card => {
            card.addEventListener('click', () => selectFighter(1, card.dataset.fighter));
        });
    }

    // Set up Player 2 grid
    const p2Grid = document.getElementById('p2-grid');
    if (p2Grid) {
        p2Grid.querySelectorAll('.character-card').forEach(card => {
            card.addEventListener('click', () => selectFighter(2, card.dataset.fighter));
        });
    }

    // Load any saved selections from session storage
    loadSavedSelections();
}

/**
 * Handle fighter selection
 * @param {number} player - Player number (1 or 2)
 * @param {string} fighterId - The fighter ID
 */
function selectFighter(player, fighterId) {
    const fighter = fighters[fighterId];
    if (!fighter) return;

    // Play selection sound
    if (typeof playSound === 'function') {
        playSound('select');
    }

    // Update state
    selectionState[`player${player}`] = fighterId;

    // Update UI
    const gridId = player === 1 ? 'p1-grid' : 'p2-grid';
    const grid = document.getElementById(gridId);

    // Remove previous selection
    grid.querySelectorAll('.character-card').forEach(card => {
        card.classList.remove('selected');
    });

    // Add selection to clicked card
    const selectedCard = grid.querySelector(`[data-fighter="${fighterId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    // Update selected fighter display
    const displayId = player === 1 ? 'p1-selected' : 'p2-selected';
    const display = document.getElementById(displayId);
    if (display) {
        display.innerHTML = `
            <img src="${fighter.image}" alt="${fighter.name}">
        `;
    }

    // Save to session storage
    sessionStorage.setItem(`player${player}Fighter`, fighterId);
    sessionStorage.setItem(`player${player}FighterName`, fighter.name);

    // Check if both players have selected
    updateFightButton();
}

/**
 * Update fight button state
 */
function updateFightButton() {
    const fightBtn = document.getElementById('fight-btn');
    if (fightBtn) {
        fightBtn.disabled = !(selectionState.player1 && selectionState.player2);
    }
}

/**
 * Load saved selections from session storage
 */
function loadSavedSelections() {
    const p1Fighter = sessionStorage.getItem('player1Fighter');
    const p2Fighter = sessionStorage.getItem('player2Fighter');

    if (p1Fighter) {
        selectFighter(1, p1Fighter);
    }
    if (p2Fighter) {
        selectFighter(2, p2Fighter);
    }
}

/**
 * Clear all selections
 */
function clearSelections() {
    selectionState.player1 = null;
    selectionState.player2 = null;
    sessionStorage.removeItem('player1Fighter');
    sessionStorage.removeItem('player2Fighter');
    sessionStorage.removeItem('player1FighterName');
    sessionStorage.removeItem('player2FighterName');

    // Reset UI
    document.querySelectorAll('.character-card').forEach(card => {
        card.classList.remove('selected');
    });

    document.querySelectorAll('.selected-fighter').forEach(display => {
        display.innerHTML = '<span>Choose Fighter</span>';
    });

    updateFightButton();
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', initCharacterSelect);

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { selectFighter, clearSelections, fighters };
}
