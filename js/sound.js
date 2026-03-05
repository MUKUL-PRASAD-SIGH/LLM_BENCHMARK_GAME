/**
 * Sound Module
 * Handles sound effects for the game
 */

// Sound file paths
const soundPaths = {
    punch: 'assets/sounds/punch.mp3',
    defend: 'assets/sounds/defend.mp3',
    victory: 'assets/sounds/victory.mp3',
    select: 'assets/sounds/select.mp3',
    background: 'assets/sounds/background.mp3',
    click: 'assets/sounds/click.mp3'
};

// Audio cache
const audioCache = {};

// Sound settings
let soundEnabled = true;
let musicEnabled = true;
let soundVolume = 0.7;
let musicVolume = 0.4;

// Background music element
let backgroundMusic = null;

/**
 * Initialize sound system
 */
function initSound() {
    // Preload sounds
    Object.keys(soundPaths).forEach(key => {
        preloadSound(key);
    });
}

/**
 * Preload a sound file
 * @param {string} soundName - Name of the sound
 */
function preloadSound(soundName) {
    const path = soundPaths[soundName];
    if (path) {
        const audio = new Audio(path);
        audio.preload = 'auto';
        audioCache[soundName] = audio;
    }
}

/**
 * Play a sound effect
 * @param {string} soundName - Name of the sound to play
 */
function playSound(soundName) {
    if (!soundEnabled) return;

    const audio = audioCache[soundName];
    if (audio) {
        // Clone the audio for overlapping sounds
        const soundClone = audio.cloneNode();
        soundClone.volume = soundVolume;
        soundClone.play().catch(err => {
            console.log('Audio play failed:', err);
        });
    } else {
        // Try to load and play
        const path = soundPaths[soundName];
        if (path) {
            const newAudio = new Audio(path);
            newAudio.volume = soundVolume;
            newAudio.play().catch(err => {
                console.log('Audio play failed:', err);
            });
        }
    }
}

/**
 * Start background music
 */
function startBackgroundMusic() {
    if (!musicEnabled) return;

    if (!backgroundMusic) {
        backgroundMusic = new Audio(soundPaths.background);
        backgroundMusic.loop = true;
        backgroundMusic.volume = musicVolume;
    }

    backgroundMusic.play().catch(err => {
        console.log('Background music failed:', err);
    });
}

/**
 * Stop background music
 */
function stopBackgroundMusic() {
    if (backgroundMusic) {
        backgroundMusic.pause();
        backgroundMusic.currentTime = 0;
    }
}

/**
 * Toggle sound effects
 * @param {boolean} enabled - Whether sound is enabled
 */
function toggleSound(enabled) {
    soundEnabled = enabled;
}

/**
 * Toggle background music
 * @param {boolean} enabled - Whether music is enabled
 */
function toggleMusic(enabled) {
    musicEnabled = enabled;
    if (enabled) {
        startBackgroundMusic();
    } else {
        stopBackgroundMusic();
    }
}

/**
 * Set sound volume
 * @param {number} volume - Volume level (0-1)
 */
function setSoundVolume(volume) {
    soundVolume = Math.max(0, Math.min(1, volume));
}

/**
 * Set music volume
 * @param {number} volume - Volume level (0-1)
 */
function setMusicVolume(volume) {
    musicVolume = Math.max(0, Math.min(1, volume));
    if (backgroundMusic) {
        backgroundMusic.volume = musicVolume;
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', function () {
    initSound();

    // Add global click sound for all buttons
    document.addEventListener('click', function (e) {
        if (e.target.closest('button')) {
            playSound('click');
        }
    });
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { playSound, startBackgroundMusic, stopBackgroundMusic, toggleSound, toggleMusic };
}
