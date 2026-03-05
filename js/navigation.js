/**
 * Navigation Module
 * Handles page switching logic between landing, selection, and arena pages
 */

/**
 * Navigate to a different page
 * @param {string} page - The page filename to navigate to
 */
function navigateTo(page) {
    // Play navigation sound if available
    if (typeof playSound === 'function') {
        playSound('select');
    }

    // Navigate to the specified page
    window.location.href = page;
}

/**
 * Go back to the previous page
 */
function goBack() {
    window.history.back();
}

/**
 * Navigate to arena with selected fighters
 */
function startFight() {
    const p1Fighter = sessionStorage.getItem('player1Fighter');
    const p2Fighter = sessionStorage.getItem('player2Fighter');

    if (p1Fighter && p2Fighter) {
        navigateTo('arena.html');
    } else {
        console.warn('Both players must select a fighter before fighting!');
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { navigateTo, goBack, startFight };
}
