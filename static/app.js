/* app.js — SER Dashboard Interactive Application Logic */

const EMOTION_EMOJIS = {
    happy: '😃',
    sad: '😢',
    angry: '😡',
    surprised: '😲',
    neutral: '😐',
    disgust: '🤢',
    fear: '😨'
};

const EMOTION_COLORS = {
    happy: '#10B981',
    sad: '#3B82F6',
    angry: '#EF4444',
    surprised: '#F59E0B',
    neutral: '#6B7280',
    disgust: '#8B5CF6',
    fear: '#EC4899'
};

// Global State
let selectedFile = null;
let mediaRecorder = null;
let audioChunks = [];
let audioContext = null;
let analyser = null;
let microphoneStream = null;
let animationFrameId = null;
let isRecording = false;
let recordStartTime = 0;
let timerInterval = null;

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    initDragAndDrop();
    initCanvas();
});

// Check API Health
async function checkHealth() {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    try {
        const response = await fetch('/health');
        if (response.ok) {
            const data = await response.json();
            indicator.className = 'status-indicator online';
            statusText.textContent = 'System Active (Model Ready)';
        } else {
            throw new Error('Health check failed');
        }
    } catch (err) {
        indicator.className = 'status-indicator offline';
        statusText.textContent = 'Backend Offline';
    }
}

// Tab Switching Logic
function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    if (tab === 'mic') {
        document.getElementById('tabMic').classList.add('active');
        document.getElementById('contentMic').classList.add('active');
    } else {
        document.getElementById('tabUpload').classList.add('active');
        document.getElementById('contentUpload').classList.add('active');
    }
}

// Canvas Waveform Initialization
function initCanvas() {
    const canvas = document.getElementById('waveformCanvas');
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    drawStaticWaveform(ctx, canvas.width, canvas.height);
}

function drawStaticWaveform(ctx, width, height) {
    ctx.strokeStyle = 'rgba(99, 102, 241, 0.3)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, height / 2);
    ctx.lineTo(width, height / 2);
    ctx.stroke();
}

// Toggle Live Microphone Recording
async function toggleRecording() {
    const btn = document.getElementById('btnRecord');
    if (!isRecording) {
        try {
            microphoneStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;

            const source = audioContext.createMediaStreamSource(microphoneStream);
            source.connect(analyser);

            mediaRecorder = new MediaRecorder(microphoneStream);
            audioChunks = [];

            mediaRecorder.ondataavailable = event => {
                if (event.data.size > 0) audioChunks.push(event.data);
            };

            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                await sendAudioBlobForAnalysis(audioBlob, 'mic_recording.wav');
            };

            mediaRecorder.start();
            isRecording = true;
            btn.classList.add('recording');
            btn.innerHTML = '<span class="btn-icon">⏹️</span> Stop & Analyze';

            startTimer();
            visualizeWaveform();
        } catch (err) {
            alert('Microphone access denied or unsupported: ' + err.message);
        }
    } else {
        stopRecording();
    }
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        if (microphoneStream) {
            microphoneStream.getTracks().forEach(track => track.stop());
        }
        if (animationFrameId) cancelAnimationFrame(animationFrameId);

        isRecording = false;
        const btn = document.getElementById('btnRecord');
        btn.classList.remove('recording');
        btn.innerHTML = '<span class="btn-icon">🔴</span> Start Recording';
        stopTimer();
    }
}

function startTimer() {
    recordStartTime = Date.now();
    timerInterval = setInterval(() => {
        const elapsedSec = Math.floor((Date.now() - recordStartTime) / 1000);
        const mins = String(Math.floor(elapsedSec / 60)).padStart(2, '0');
        const secs = String(elapsedSec % 60).padStart(2, '0');
        document.getElementById('recTimer').textContent = `${mins}:${secs}`;
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
    document.getElementById('recTimer').textContent = '00:00';
}

function visualizeWaveform() {
    const canvas = document.getElementById('waveformCanvas');
    const ctx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    function draw() {
        if (!isRecording) return;
        animationFrameId = requestAnimationFrame(draw);
        analyser.getByteTimeDomainData(dataArray);

        ctx.fillStyle = 'rgba(11, 15, 25, 0.4)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.lineWidth = 2;
        ctx.strokeStyle = '#6366F1';
        ctx.beginPath();

        const sliceWidth = canvas.width * 1.0 / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = v * canvas.height / 2;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);

            x += sliceWidth;
        }

        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.stroke();
    }
    draw();
}

// Drag and Drop Uploader Logic
function initDragAndDrop() {
    const dropZone = document.getElementById('dropZone');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('drag-over'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('drag-over'), false);
    });

    dropZone.addEventListener('drop', e => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) processFile(files[0]);
    });
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) processFile(files[0]);
}

function processFile(file) {
    selectedFile = file;
    document.getElementById('dropZone').style.display = 'none';
    const preview = document.getElementById('filePreview');
    preview.style.display = 'block';

    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';

    const player = document.getElementById('audioPlayer');
    player.src = URL.createObjectURL(file);
}

function analyzeSelectedFile() {
    if (selectedFile) {
        sendAudioBlobForAnalysis(selectedFile, selectedFile.name);
    }
}

// API Call: Send Audio Blob to /api/v1/predict
async function sendAudioBlobForAnalysis(blob, filename) {
    showLoading(true);

    const formData = new FormData();
    formData.append('file', blob, filename);

    try {
        const response = await fetch('/api/v1/predict', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || 'Prediction failed');
        }

        const data = await response.json();
        renderResults(data);
    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        showLoading(false);
    }
}

// Render Results on Screen
function renderResults(data) {
    document.getElementById('placeholderState').style.display = 'none';
    const resultsContent = document.getElementById('resultsContent');
    resultsContent.style.display = 'block';

    const latencyBadge = document.getElementById('latencyBadge');
    latencyBadge.style.display = 'inline-block';
    latencyBadge.textContent = `⚡ ${data.inference_latency_ms}ms`;

    const emotion = data.predicted_class.toLowerCase();
    const confidencePct = (data.confidence_score * 100).toFixed(1);

    // Hero Winner Card
    const heroCard = document.getElementById('winnerHero');
    heroCard.className = `winner-hero theme-${emotion}`;
    document.getElementById('winnerEmoji').textContent = EMOTION_EMOJIS[emotion] || '🎙️';
    document.getElementById('winnerTitle').textContent = emotion.toUpperCase();
    document.getElementById('winnerConfidence').textContent = `${confidencePct}% Confidence`;

    // Probability Bars
    const barsContainer = document.getElementById('probabilityBars');
    barsContainer.innerHTML = '';

    const dist = data.probability_distribution;
    // Sort emotions by probability descending
    const sortedEmotions = Object.keys(dist).sort((a, b) => dist[b] - dist[a]);

    sortedEmotions.forEach(emo => {
        const prob = dist[emo];
        const pct = (prob * 100).toFixed(1);
        const color = EMOTION_COLORS[emo] || '#6366F1';

        const row = document.createElement('div');
        row.className = 'bar-row';
        row.innerHTML = `
            <span class="bar-label">${emo}</span>
            <div class="bar-track">
                <div class="bar-fill" style="width: 0%; background-color: ${color};"></div>
            </div>
            <span class="bar-percentage">${pct}%</span>
        `;
        barsContainer.appendChild(row);

        // Trigger CSS transition animation after append
        setTimeout(() => {
            row.querySelector('.bar-fill').style.width = `${pct}%`;
        }, 50);
    });
}

function showLoading(show) {
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}
