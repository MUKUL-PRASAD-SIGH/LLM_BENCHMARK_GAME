/**
 * avatar-maker.js
 * Deep Learning Face Swap Edition
 * Uploads 4-5 photos to the local FastAPI Python engine to generate perfect 3D swap.
 */

const AvatarMaker = (() => {
    // ---- State ----
    let selectedFiles = [];       // Array of uploaded File objects
    let generatedFaceDataUrl = null; // Base64 of the final ML-generated face
    let currentGender = 'male';
    let currentBody   = '1';
    let currentSide   = 'p1';

    // -------------------------------------------------------
    //  PUBLIC: open/close the wizard
    // -------------------------------------------------------
    function open(side) {
        currentSide = side || 'p1';
        document.getElementById('avatar-wizard-overlay').style.display = 'flex';
        reset();
    }

    function close() {
        document.getElementById('avatar-wizard-overlay').style.display = 'none';
    }

    function reset() {
        selectedFiles = [];
        generatedFaceDataUrl = null;
        document.getElementById('av-file-input').value = '';
        document.getElementById('av-thumbnails').innerHTML = '';
        document.getElementById('av-upload-text').innerHTML = 'CLICK TO UPLOAD 4-5 PHOTOS<br>For optimum 3D face structure';
        document.getElementById('av-upload-next-btn').style.display = 'none';
        
        document.getElementById('av-step-gender').style.display = 'none';
        document.getElementById('av-step-body').style.display = 'none';
        document.getElementById('av-step-preview').style.display = 'none';
        document.getElementById('av-step-upload').style.display = 'flex';
        
        // Reset preview state
        document.getElementById('av-loading-spinner').style.display = 'none';
        document.getElementById('av-fighter-container').style.display = 'flex';
        document.getElementById('av-btn-generate').style.display = 'block';
        document.getElementById('av-btn-confirm').style.display = 'none';
        document.getElementById('av-preview-hint').innerHTML = 'FINAL PREVIEW<br>Click Generate to run the Deep Learning Face Swap Engine.';
        
        syncFighterPreview();
    }

    // -------------------------------------------------------
    //  STEP 1 – Multi Photo upload
    // -------------------------------------------------------
    function onFilesSelected(files) {
        if (!files || files.length === 0) return;
        
        // Allow user to incrementally add files or replace
        for (let i = 0; i < files.length; i++) {
            if (files[i].type.startsWith('image/')) {
                selectedFiles.push(files[i]);
            }
        }
        
        // Render thumbnails
        const container = document.getElementById('av-thumbnails');
        container.innerHTML = '';
        selectedFiles.forEach(file => {
            const url = URL.createObjectURL(file);
            const img = document.createElement('img');
            img.src = url;
            img.style.width = '40px';
            img.style.height = '40px';
            img.style.objectFit = 'cover';
            img.style.borderRadius = '5px';
            container.appendChild(img);
        });
        
        document.getElementById('av-upload-text').innerHTML = `${selectedFiles.length} PHOTOS UPLOADED.<br>Upload more to improve accuracy.`;
        document.getElementById('av-upload-next-btn').style.display = 'block';
    }

    // -------------------------------------------------------
    //  STEP 2 & 3 – Gender & Template
    // -------------------------------------------------------
    function selectGender(gender) {
        currentGender = gender;
        document.querySelectorAll('.av-gender-btn').forEach(b => b.classList.toggle('active', b.dataset.gender === gender));
        syncFighterPreview();
    }

    function selectBody(bodyId) {
        currentBody = bodyId;
        document.querySelectorAll('.av-body-btn').forEach(b => b.classList.toggle('active', b.dataset.body === bodyId));
        syncFighterPreview();
    }

    // -------------------------------------------------------
    //  GENERATE – Call Python ML Engine
    // -------------------------------------------------------
    async function generateAvatar() {
        if (selectedFiles.length === 0) {
            alert("No photos uploaded!");
            return;
        }

        // Show loading state
        document.getElementById('av-btn-generate').style.display = 'none';
        document.getElementById('av-fighter-container').style.display = 'none';
        document.getElementById('av-loading-spinner').style.display = 'block';
        document.getElementById('av-preview-hint').innerHTML = 'EXTRACTING 3D MESH<br>Please wait...';

        const bodyMap = {
            male: { '1': 'boxer_male', '2': 'demon_male', '3': 'vampire_male', '4': 'brawler_male' },
            female: { '1': 'boxer_female', '2': 'demon_female', '3': 'vampire_female', '4': 'brawler_female' }
        };
        const templateId = (bodyMap[currentGender] || bodyMap.male)[currentBody] || 'boxer_male';

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('images', file);
        });
        formData.append('template_id', templateId);

        try {
            // Note: This API server is expected to run on port 8000
            const response = await fetch('http://127.0.0.1:8000/api/v1/generate_avatar', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Server error');
            }

            const data = await response.json();
            generatedFaceDataUrl = data.avatar_data_url;

            // Success: update UI
            document.getElementById('av-loading-spinner').style.display = 'none';
            document.getElementById('av-fighter-container').style.display = 'flex';
            document.getElementById('av-btn-generate').style.display = 'none';
            document.getElementById('av-btn-confirm').style.display = 'block';
            document.getElementById('av-preview-hint').innerHTML = 'GENERATION COMPLETE!<br>Here is your 2.5D fighter face.';
            syncFighterPreview();

        } catch (e) {
            console.error(e);
            alert("Failed to generate avatar: " + e.message);
            // Restore UI for retry
            document.getElementById('av-loading-spinner').style.display = 'none';
            document.getElementById('av-fighter-container').style.display = 'flex';
            document.getElementById('av-btn-generate').style.display = 'block';
            document.getElementById('av-preview-hint').innerHTML = 'FINAL PREVIEW<br>Click Generate to run the Deep Learning Face Swap Engine.';
        }
    }

    // -------------------------------------------------------
    //  LIVE PREVIEW (CSS sync)
    // -------------------------------------------------------
    function syncFighterPreview() {
        const pf = document.getElementById('av-preview-fighter');
        if (!pf) return;

        // Determine body class from gender + template
        const bodyMap = {
            male: { '1': 'player1', '2': 'player3', '3': 'player4', '4': 'player1' },
            female: { '1': 'player2', '2': 'player3', '3': 'player4', '4': 'player2' }
        };
        const playerClass = (bodyMap[currentGender] || bodyMap.male)[currentBody] || 'player1';
        pf.className = `fighter ${playerClass} idle`;

        const headEl = pf.querySelector('.piece.head');
        if (headEl && generatedFaceDataUrl) {
            headEl.style.backgroundImage = `url('${generatedFaceDataUrl}')`;
            headEl.style.backgroundSize = 'cover';
            headEl.style.backgroundPosition = 'center top';
            headEl.style.overflow = 'hidden';
            headEl.style.borderRadius = '50%';
            ['hair', 'eye', 'headband', 'mouthguard', 'mask', 'peek-eye'].forEach(cls => {
                const el = headEl.querySelector('.' + cls);
                if (el) el.style.display = 'none';
            });
            const ear = headEl.querySelector('.ear');
            if (ear) ear.style.display = 'block';
        } else if (headEl) {
            headEl.style.backgroundImage = '';
            headEl.style.borderRadius = '';
            ['hair', 'eye', 'headband', 'mouthguard', 'mask', 'peek-eye', 'ear'].forEach(cls => {
                const el = headEl.querySelector('.' + cls);
                if (el) el.style.display = '';
            });
        }
    }

    // -------------------------------------------------------
    //  CONFIRM – Save to sessionStorage
    // -------------------------------------------------------
    function confirm() {
        if (!generatedFaceDataUrl) return;
        
        const bodyMap = {
            male: { '1': 'player1', '2': 'player3', '3': 'player4', '4': 'player1' },
            female: { '1': 'player2', '2': 'player3', '3': 'player4', '4': 'player2' }
        };
        const playerClass = (bodyMap[currentGender] || bodyMap.male)[currentBody] || 'player1';
        const avatarData = {
            faceDataUrl: generatedFaceDataUrl,
            playerClass,
            gender: currentGender,
            bodyTemplate: currentBody
        };
        
        sessionStorage.setItem(`avatar_${currentSide}`, JSON.stringify(avatarData));
        applyAvatarToFighter(currentSide, avatarData);
        close();
        
        if (typeof window.onAvatarConfirmed === 'function') {
            window.onAvatarConfirmed(currentSide, avatarData);
        }
    }

    // -------------------------------------------------------
    //  APPLY – inject face into arena fighter element
    // -------------------------------------------------------
    function applyAvatarToFighter(side, avatarData) {
        if (!avatarData || !avatarData.faceDataUrl) return;
        const fighterNum = side === 'p1' ? 1 : 2;
        const fighterEl = document.getElementById(`fighter${fighterNum}`);
        if (!fighterEl) return;
        
        const isFacingLeft = fighterEl.classList.contains('facing-left');
        const currentAnim = [...fighterEl.classList].find(c =>
            ['idle','boxing','kicking','defend','duck','hit','victory','defeated','move-forward','move-backward'].includes(c)) || 'idle';
        
        fighterEl.className = `fighter ${avatarData.playerClass} ${currentAnim}${isFacingLeft ? ' facing-left' : ''}`;
        
        const headEl = fighterEl.querySelector('.piece.head');
        if (headEl) {
            headEl.style.backgroundImage = `url('${avatarData.faceDataUrl}')`;
            headEl.style.backgroundSize = 'cover';
            headEl.style.backgroundPosition = 'center top';
            headEl.style.borderRadius = '50%';
            headEl.style.overflow = 'hidden';
            ['hair', 'eye', 'headband', 'mouthguard', 'mask', 'peek-eye'].forEach(cls => {
                const el = headEl.querySelector('.' + cls);
                if (el) el.style.display = 'none';
            });
        }
    }

    function restoreAvatars() {
        ['p1', 'p2'].forEach(side => {
            const raw = sessionStorage.getItem(`avatar_${side}`);
            if (raw) {
                try { applyAvatarToFighter(side, JSON.parse(raw)); } catch(e) {}
            }
        });
    }

    // Navigation
    function goToGender() {
        document.getElementById('av-step-upload').style.display = 'none';
        document.getElementById('av-step-gender').style.display = 'flex';
    }
    function goToBody() {
        document.getElementById('av-step-gender').style.display = 'none';
        document.getElementById('av-step-body').style.display = 'flex';
    }
    function goToPreview() {
        document.getElementById('av-step-body').style.display = 'none';
        document.getElementById('av-step-preview').style.display = 'flex';
        syncFighterPreview();
    }
    function backToUpload() {
        document.getElementById('av-step-gender').style.display = 'none';
        document.getElementById('av-step-upload').style.display = 'flex';
    }
    function backToGender() {
        document.getElementById('av-step-body').style.display = 'none';
        document.getElementById('av-step-gender').style.display = 'flex';
    }
    function backToBody() {
        document.getElementById('av-step-preview').style.display = 'none';
        document.getElementById('av-step-body').style.display = 'flex';
    }

    return {
        open, close, reset, confirm, restoreAvatars, generateAvatar,
        onFilesSelected, selectGender, selectBody,
        goToGender, goToBody, goToPreview,
        backToUpload, backToGender, backToBody
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('fighter1')) {
        AvatarMaker.restoreAvatars();
    }
});
