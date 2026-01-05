// content.js
let socket = null;
let mediaStream = null;
let audioContext = null;
let processor = null;
let isRecording = false;

const TARGET_SAMPLE_RATE = 16000;
const WEBSOCKET_URL = "ws://127.0.0.1:8000/ws/asr";

// Indicateur visuel (HUD)
let hud = null;

function createHUD() {
    if (hud) return;
    hud = document.createElement('div');
    hud.style.position = 'fixed';
    hud.style.bottom = '20px';
    hud.style.right = '20px';
    hud.style.padding = '10px 20px';
    hud.style.backgroundColor = '#333';
    hud.style.color = 'white';
    hud.style.borderRadius = '5px';
    hud.style.zIndex = '999999';
    hud.style.fontFamily = 'Arial, sans-serif';
    hud.style.boxShadow = '0 2px 10px rgba(0,0,0,0.3)';
    hud.style.display = 'none';
    hud.innerText = 'ASR Inactif';
    document.body.appendChild(hud);
}

function updateHUD(status, type) {
    if (!hud) createHUD();
    hud.style.display = 'block';
    hud.innerText = status;
    
    if (type === 'recording') {
        hud.style.backgroundColor = '#d32f2f'; // Rouge
    } else if (type === 'connecting') {
        hud.style.backgroundColor = '#fbc02d'; // Jaune
        hud.style.color = 'black';
    } else {
        hud.style.backgroundColor = '#333'; // Gris
        hud.style.color = 'white';
        // Cacher après 2 secondes si inactif
        setTimeout(() => {
            if (!isRecording) hud.style.display = 'none';
        }, 2000);
    }
}

// Écoute les messages (du background ou du popup)
browser.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "insertText") {
        insertTextAtCursor(request.text);
    } else if (request.action === "toggle_recording") {
        toggleRecording();
    }
});

function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        updateHUD("Connexion...", "connecting");
        
        socket = new WebSocket(WEBSOCKET_URL);
        
        socket.onopen = async () => {
            updateHUD("Micro...", "connecting");
            try {
                // Demander l'accès au micro (déclenchera une popup de permission du navigateur)
                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                setupAudioProcessing(mediaStream);
                
                isRecording = true;
                updateHUD("🔴 Enregistrement...", "recording");
            } catch (err) {
                console.error(err);
                updateHUD("Erreur Micro: " + err.message, "error");
                socket.close();
            }
        };

        socket.onmessage = (event) => {
            const text = event.data;
            if (text) {
                insertTextAtCursor(" " + text.trim());
            }
        };

        socket.onerror = (error) => {
            console.error("WebSocket Error:", error);
            // L'erreur sera traitée dans le onclose
        };
        
        socket.onclose = (event) => {
            if (isRecording) stopRecording();
            
            if (event.code === 1006) {
                updateHUD("Erreur: Firefox bloque WS.\nDésactivez 'Mode HTTPS uniquement'", "error");
            }
        };

    } catch (err) {
        console.error(err);
        updateHUD("Erreur Init: " + err.message, "error");
    }
}

function stopRecording() {
    isRecording = false;
    updateHUD("Arrêté", "idle");

    if (processor) {
        processor.disconnect();
        processor = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
}

function setupAudioProcessing(stream) {
    audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);

    source.connect(processor);
    processor.connect(audioContext.destination);

    processor.onaudioprocess = (e) => {
        if (!isRecording || socket.readyState !== WebSocket.OPEN) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const downsampledBuffer = downsampleBuffer(inputData, audioContext.sampleRate, TARGET_SAMPLE_RATE);
        socket.send(downsampledBuffer);
    };
}

// Fonction utilitaire d'insertion de texte
function insertTextAtCursor(text) {
    const el = document.activeElement;
    if (!el) return;

    // Méthode 1 : execCommand
    try {
        if (document.queryCommandSupported('insertText')) {
            const success = document.execCommand('insertText', false, text);
            if (success) return; 
        }
    } catch (e) {
        console.warn("ASR: execCommand failed", e);
    }

    // Méthode 2 : InputEvent moderne (Spécial Google Docs / Frameworks récents)
    // Si execCommand a échoué, on tente de simuler un événement de saisie directe
    try {
        const inputEvent = new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            inputType: 'insertText',
            data: text,
            view: window
        });
        el.dispatchEvent(inputEvent);
        // Si Google Docs a intercepté ça, le texte devrait apparaître.
        // On continue quand même vers les fallbacks si l'élément est un input standard vide
    } catch (e) {
        console.warn("ASR: InputEvent failed", e);
    }

    // Méthode 3 : Fallback pour les champs standards (Input / Textarea)
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
        const start = el.selectionStart;
        const end = el.selectionEnd;
        const value = el.value;
        
        el.value = value.substring(0, start) + text + value.substring(end);
        el.selectionStart = el.selectionEnd = start + text.length;
        el.dispatchEvent(new Event('input', { bubbles: true }));
    } 
    // Méthode 3 : Fallback manuel pour les éditeurs riches (ContentEditable)
    // Si execCommand a échoué mais qu'on est dans une zone éditable
    else if (el.isContentEditable) {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.deleteContents();
            const textNode = document.createTextNode(text);
            range.insertNode(textNode);
            range.setStartAfter(textNode);
            range.setEndAfter(textNode);
            selection.removeAllRanges();
            selection.addRange(range);
            
            // Tenter de déclencher un événement d'input pour réveiller l'éditeur
            el.dispatchEvent(new Event('input', { bubbles: true }));
        }
    } 
}

// ... (Fonctions de conversion audio identiques à popup.js)
function downsampleBuffer(buffer, sampleRate, outSampleRate) {
    if (outSampleRate === sampleRate) return convertFloat32ToInt16(buffer);
    const sampleRateRatio = sampleRate / outSampleRate;
    const newLength = Math.round(buffer.length / sampleRateRatio);
    const result = new Int16Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
        let accum = 0, count = 0;
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
            accum += buffer[i];
            count++;
        }
        const s = Math.max(-1, Math.min(1, accum / count));
        result[offsetResult] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        offsetResult++;
        offsetBuffer = nextOffsetBuffer;
    }
    return result;
}

function convertFloat32ToInt16(buffer) {
    let l = buffer.length;
    let buf = new Int16Array(l);
    while (l--) {
        const s = Math.max(-1, Math.min(1, buffer[l]));
        buf[l] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return buf;
}