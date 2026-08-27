
// ==================== ADVANCED PRIORITY PREVIEW ====================
const categoryRisk = {
    'Pothole': 65, 'Garbage': 35, 'Water Leakage': 70,
    'Streetlight': 45, 'Sewage': 75, 'Noise Pollution': 20,
    'Illegal Dumping': 40, 'Road Damage': 70, 'Traffic Signal': 80, 'Other': 25
};

const emergencyKeywords = [
    'accident', 'injured', 'injury', 'death', 'collapse', 'flooding', 'flood',
    'fire', 'burning', 'electrocution', 'child', 'children', 'school', 'hospital',
    'danger', 'dangerous', 'life threatening', 'emergency', 'sinkhole', 'gas leak',
    'toxic', 'drowning', 'trapped'
];

const severityKeywords = {
    'major': 15, 'massive': 20, 'huge': 15, 'deep': 15, 'large': 10,
    'overflowing': 20, 'burst': 25, 'broken': 10, 'destroyed': 20,
    'blocked': 15, 'daily': 10, 'frequent': 10, 'multiple': 10,
    'spreading': 15, 'stinking': 15, 'contaminated': 20,
    'accidents': 20, 'damage': 15, 'vehicles': 10, 'completely': 15, 'worst': 20
};

function calculatePriorityPreview() {
    const category = document.getElementById('categorySelect').value;
    const desc = (document.getElementById('descriptionInput').value || '').toLowerCase();
    const preview = document.getElementById('priorityPreview');
    const badge = document.getElementById('priorityBadge');
    const factors = document.getElementById('priorityFactors');

    if (!category) { preview.style.display = 'none'; return; }

    let score = categoryRisk[category] || 25;
    let factorList = [`Base: ${category} (${score})`];

    // Emergency keyword check
    for (const kw of emergencyKeywords) {
        if (desc.includes(kw)) {
            score = 98;
            factorList = [`Emergency: "${kw}" detected`];
            break;
        }
    }

    // Severity keywords
    if (score < 98) {
        let boost = 0;
        let matched = [];
        for (const [kw, val] of Object.entries(severityKeywords)) {
            if (desc.includes(kw)) { boost += val; matched.push(kw); }
        }
        boost = Math.min(boost, 35);
        if (boost > 0) {
            score += boost;
            factorList.push(`Severity: ${matched.slice(0,3).join(', ')} (+${boost})`);
        }

        // Word count
        const words = desc.split(/\s+/).filter(w => w).length;
        if (words > 50) { score += 8; factorList.push(`Detail: ${words} words (+8)`); }
        else if (words > 25) { score += 4; factorList.push(`Detail: ${words} words (+4)`); }

        // Media check
        const hasImg = document.querySelector('input[name="image"]')?.files?.length > 0;
        const hasVid = document.querySelector('input[name="video"]')?.files?.length > 0;
        if (hasImg && hasVid) { score += 12; factorList.push('Evidence: Photo+Video (+12)'); }
        else if (hasImg) { score += 7; factorList.push('Evidence: Photo (+7)'); }
        else if (hasVid) { score += 10; factorList.push('Evidence: Video (+10)'); }

        // Time context
        const hour = new Date().getHours();
        if (category === 'Streetlight' && (hour >= 18 || hour <= 6)) {
            score += 15; factorList.push('Time: Dark hours (+15)');
        }
    }

    score = Math.max(0, Math.min(100, score));

    let priority, icon;
    if (score >= 80) { priority = 'Urgent'; icon = 'fa-bolt'; }
    else if (score >= 60) { priority = 'High'; icon = 'fa-exclamation-circle'; }
    else if (score >= 40) { priority = 'Medium'; icon = 'fa-exclamation-triangle'; }
    else if (score >= 20) { priority = 'Low'; icon = 'fa-info-circle'; }
    else { priority = 'Info'; icon = 'fa-comment'; }

    preview.style.display = 'block';
    badge.textContent = `${priority} (${score}/100)`;
    badge.className = 'priority-badge priority-' + priority.toLowerCase();
    factors.innerHTML = factorList.map(f => `<span class="factor-tag"><i class="fas fa-caret-right"></i> ${f}</span>`).join('');
}

document.getElementById('categorySelect').addEventListener('change', calculatePriorityPreview);
document.getElementById('descriptionInput').addEventListener('input', function() {
    clearTimeout(this._debounce);
    this._debounce = setTimeout(calculatePriorityPreview, 400);
});

// --- Multilingual Voice Recording Logic ---
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

function toggleVoiceRecording() {
    const btn = document.getElementById('voiceBtn');
    const text = document.getElementById('voiceBtnText');
    const wave = document.getElementById('voiceRecordingWave');
    const status = document.getElementById('descEnhanceStatus');

    if (!isRecording) {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                mediaRecorder.onstop = sendVoiceData;
                
                mediaRecorder.start();
                isRecording = true;
                btn.style.background = "var(--danger)";
                btn.style.color = "white";
                text.innerText = "Stop Recording";
                wave.style.display = 'flex';
                status.innerHTML = '<span style="color: var(--danger);"><i class="fas fa-circle fa-beat"></i> Listening carefully... Speak in any language.</span>';
            })
            .catch(err => {
                console.error("Mic error:", err);
                status.innerHTML = '<span style="color: var(--danger);">Microphone access denied.</span>';
            });
    } else {
        mediaRecorder.stop();
        isRecording = false;
        btn.style.background = "rgba(239, 68, 68, 0.1)";
        btn.style.color = "var(--danger)";
        text.innerText = "Processing...";
        wave.style.display = 'none';
        btn.disabled = true;
    }
}

function sendVoiceData() {
    const status = document.getElementById('descEnhanceStatus');
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append('audio', audioBlob);

    status.innerHTML = '<span style="color: var(--accent);"><i class="fas fa-robot"></i> Groq AI is transcribing your regional audio...</span>';

    fetch('/api/voice-report', {
        method: 'POST',
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        const btn = document.getElementById('voiceBtn');
        const text = document.getElementById('voiceBtnText');
        btn.disabled = false;
        text.innerText = "Record Voice";

        if (data.clean_description) {
            document.getElementById('descriptionInput').value = data.clean_description;
            if (data.category) {
                const select = document.getElementById('categorySelect');
                for(let i=0; i<select.options.length; i++) {
                    if(select.options[i].value.includes(data.category)) {
                        select.selectedIndex = i;
                        select.dispatchEvent(new Event('change'));
                        break;
                    }
                }
            }
            status.innerHTML = `<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Transcribed: "${data.native_transcript.substring(0, 50)}..."</span>`;
        } else {
            status.innerHTML = `<span style="color: var(--danger);">${data.error || 'Transcription failed.'}</span>`;
        }
    })
    .catch(e => {
        console.error(e);
        status.innerHTML = '<span style="color: var(--danger);">Network error in voice processing.</span>';
        document.getElementById('voiceBtn').disabled = false;
        document.getElementById('voiceBtnText').innerText = "Record Voice";
    });
}
function enhanceDescription() {
    const desc = document.getElementById('descriptionInput').value.trim();
    const btn = document.getElementById('enhanceDescBtn');
    const status = document.getElementById('descEnhanceStatus');

    if (!desc) {
        status.innerHTML = '<span style="color: var(--warning);"><i class="fas fa-exclamation-triangle"></i> Please write a description first.</span>';
        setTimeout(() => status.innerHTML = '', 3000);
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
    status.innerHTML = '<span style="color: var(--accent);"><i class="fas fa-robot"></i> AI Smart Analyzer is processing...</span>';

    fetch('/api/analyze-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: desc })
    })
    .then(res => res.json())
    .then(data => {
        if (data.official_description && !data.error) {
            document.getElementById('descriptionInput').value = data.official_description;
            
            if (data.category && document.getElementById('categorySelect').value === "") {
                const select = document.getElementById('categorySelect');
                for(let i=0; i<select.options.length; i++) {
                    if(select.options[i].value.includes(data.category)) {
                        select.selectedIndex = i;
                        // trigger change event
                        const event = new Event('change');
                        select.dispatchEvent(event);
                        break;
                    }
                }
            }

            let msg = `<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Cleaned & optimized. Severity: ${data.severity_score}/10!</span>`;
            if (data.missing_details && data.missing_details.toLowerCase() !== "none") {
                msg += `<br><span style="color: var(--warning); margin-top:5px; display:inline-block;"><i class="fas fa-info-circle"></i> <b>AI Suggests:</b> ${data.missing_details}</span>`;
            }
            status.innerHTML = msg;
        } else {
            status.innerHTML = '<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> ' + (data.error || 'Could not analyze.') + '</span>';
        }
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> AI Analyze';
    })
    .catch(() => {
        status.innerHTML = '<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> Check failed. Try again.</span>';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> AI Analyze';
    });
}

// AI Enhance Location
function enhanceLocation() {
    const loc = document.getElementById('locationInput').value.trim();
    const lat = document.getElementById('latitudeInput').value;
    const lng = document.getElementById('longitudeInput').value;
    const btn = document.getElementById('enhanceLocBtn');
    const status = document.getElementById('locEnhanceStatus');

    if (!loc && (!lat || !lng)) {
        status.innerHTML = '<span style="color: var(--warning);"><i class="fas fa-exclamation-triangle"></i> Please select a location on the map first.</span>';
        setTimeout(() => status.innerHTML = '', 3000);
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refine...';
    status.innerHTML = '<span style="color: var(--accent);"><i class="fas fa-robot"></i> AI hyper-accurate engine running...</span>';

    fetch('/api/enhance-location', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ location: loc, latitude: lat, longitude: lng })
    })
    .then(res => res.json())
    .then(data => {
        if (data.refined_address && !data.error) {
            document.getElementById('locationInput').value = data.refined_address;
            let msg = '<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Location refined! (Conf: '+data.confidence_score+'%)</span>';
            if(data.nearby_landmarks && data.nearby_landmarks.length > 0) {
                msg += '<br><span style="color: var(--info); display:inline-block; margin-top:5px;"><i class="fas fa-map-pin"></i> <b>Landmarks:</b> ' + data.nearby_landmarks.join(', ') + '</span>';
            }
            status.innerHTML = msg;
        } else {
            status.innerHTML = '<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> ' + (data.error || 'Could not refine.') + '</span>';
        }
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> AI Enhance';
    })
    .catch(() => {
        status.innerHTML = '<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> Enhancement failed. Try again.</span>';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-magic"></i> AI Enhance';
    });
}

function checkDuplicates(lat, lon) {
    if (!lat || !lon) return;
    fetch('/api/nearby-duplicates', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latitude: lat, longitude: lon })
    }).then(res => res.json()).then(data => {
        const dupDiv = document.getElementById('duplicateWarning');
        if (data.length > 0) {
            dupDiv.style.display = 'block';
            let html = '<h5 style="margin-bottom: 8px; color: var(--warning);"><i class="fas fa-copy"></i> Similar Reports Nearby</h5>';
            html += '<p style="margin-bottom: 8px; font-size: 13px;">Consider upvoting instead of creating a duplicate to boost urgency!</p>';
            html += '<ul style="padding-left: 20px; font-size: 13px; margin-bottom: 0;">';
            data.forEach(d => {
                html += `<li style="margin-bottom: 4px;"><a href="/complaint/${d.id}" target="_blank" style="color: var(--info); text-decoration: underline;">#${d.id} - ${d.category}</a> (${d.distance_m}m away - ${d.status})</li>`;
            });
            html += '</ul>';
            dupDiv.innerHTML = html;
        } else {
            dupDiv.style.display = 'none';
        }
    }).catch(e => console.error(e));
}

// MULTIMEDIA PREVIEW & VALIDATION
function previewMedia(input, previewId) {
    const previewDiv = document.getElementById(previewId);
    if (input.files && input.files[0]) {
        const file = input.files[0];
        const reader = new FileReader();
        
        reader.onload = function(e) {
            previewDiv.style.display = 'block';
            if (previewId === 'img-preview') {
                previewDiv.querySelector('img').src = e.target.result;
            } else {
                previewDiv.querySelector('video').src = e.target.result;
            }
        }
        reader.readAsDataURL(file);
    }
}

function validateVideo(input) {
    const error = document.getElementById('videoError');
    const previewDiv = document.getElementById('vid-preview');
    error.innerText = "";
    
    if (input.files && input.files[0]) {
        const file = input.files[0];
        if (file.size > 20 * 1024 * 1024) { // 20MB limit
            error.innerText = "❌ File too large (Max 20MB)";
            input.value = "";
            previewDiv.style.display = 'none';
            return;
        }

        const video = document.createElement('video');
        video.preload = 'metadata';
        video.onloadedmetadata = function() {
            window.URL.revokeObjectURL(video.src);
            if (video.duration > 15.5) {
                error.innerText = "❌ Video must be 15 seconds or less.";
                input.value = "";
                previewDiv.style.display = 'none';
            } else {
                previewMedia(input, 'vid-preview');
            }
        }
        video.src = URL.createObjectURL(file);
    }
}
document.getElementById('reportForm').addEventListener('submit', function(e) {
    const btn = document.getElementById('submitBtn');
    const btnText = btn.querySelector('.btn-text');
    const btnLoader = btn.querySelector('.btn-loader');
    
    btn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline-block';
    
    // Add submission ripple 
    const ripple = document.createElement('div');
    ripple.className = 'submit-ripple';
    btn.appendChild(ripple);
});
