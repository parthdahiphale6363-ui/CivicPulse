
// ==================== LEAFLET MAP INITIALIZATION ====================
let reportMap, reportMarker, accuracyCircle;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize map centered on India (default)
    reportMap = L.map('locationMap', {
        zoomControl: true,
        attributionControl: false
    }).setView([20.5937, 78.9629], 5);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(reportMap);

    // Click to place marker
    reportMap.on('click', function(e) {
        placeMarker(e.latlng.lat, e.latlng.lng);
        reverseGeocode(e.latlng.lat, e.latlng.lng);
    });

    // Fix map render on tab/scroll visibility
    setTimeout(() => reportMap.invalidateSize(), 300);
});

function placeMarker(lat, lng) {
    if (reportMarker) {
        reportMarker.setLatLng([lat, lng]);
    } else {
        reportMarker = L.marker([lat, lng], { draggable: true }).addTo(reportMap);
        reportMarker.on('dragend', function(e) {
            const pos = e.target.getLatLng();
            reverseGeocode(pos.lat, pos.lng);
            updateCoords(pos.lat, pos.lng);
        });
    }
    reportMap.setView([lat, lng], Math.max(reportMap.getZoom(), 15));
    updateCoords(lat, lng);
    document.getElementById('mapOverlay').style.display = 'none';
}

function updateCoords(lat, lng) {
    document.getElementById('latitudeInput').value = lat;
    document.getElementById('longitudeInput').value = lng;
    document.getElementById('coordLat').textContent = lat.toFixed(6);
    document.getElementById('coordLng').textContent = lng.toFixed(6);
    document.getElementById('coordsDisplay').style.display = 'block';
    checkDuplicates(lat, lng);
}

function reverseGeocode(lat, lng) {
    const input = document.getElementById('locationInput');
    const status = document.getElementById('locEnhanceStatus');
    status.innerHTML = '<span style="color: var(--accent);"><i class="fas fa-spinner fa-spin"></i> Resolving address...</span>';

    fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&addressdetails=1`)
        .then(r => r.json())
        .then(data => {
            if (data.display_name) {
                input.value = data.display_name;
                status.innerHTML = '<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Address resolved!</span>';
            } else {
                input.value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
                status.innerHTML = '<span style="color: var(--warning);">Using coordinates (no address found)</span>';
            }
        })
        .catch(() => {
            input.value = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            status.innerHTML = '<span style="color: var(--warning);">Network error. Using coordinates.</span>';
        });
}

// ==================== HIGH-ACCURACY GPS ====================
let gpsWatchId = null;
let gpsTimeoutId = null;

function getCurrentLocation() {
    const btn = document.getElementById('gpsBtn');
    const status = document.getElementById('locEnhanceStatus');

    if (!navigator.geolocation) {
        status.innerHTML = '<span style="color: var(--danger);">GPS not supported by your browser</span>';
        return;
    }

    if (gpsWatchId) {
        navigator.geolocation.clearWatch(gpsWatchId);
        clearTimeout(gpsTimeoutId);
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Acquiring GPS...';
    status.innerHTML = '<span style="color: var(--info);"><i class="fas fa-satellite-dish"></i> Requesting high-accuracy satellite fix...</span>';

    // Timeout after 15 seconds if we can't get a good fix
    gpsTimeoutId = setTimeout(() => {
        if(gpsWatchId) navigator.geolocation.clearWatch(gpsWatchId);
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-crosshairs"></i> 📍 High-Accuracy GPS';
        status.innerHTML += '<br><span style="color: var(--warning); font-size: 11px;">GPS search timed out. Using best available accuracy.</span>';
    }, 15000);

    gpsWatchId = navigator.geolocation.watchPosition(
        (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            const acc = position.coords.accuracy; // meters

            placeMarker(lat, lon);
            reverseGeocode(lat, lon);
            reportMap.setView([lat, lon], 17);

            // Show accuracy circle
            if (accuracyCircle) reportMap.removeLayer(accuracyCircle);
            accuracyCircle = L.circle([lat, lon], {
                radius: acc, color: '#6366f1', fillColor: '#6366f1',
                fillOpacity: 0.08, weight: 1, dashArray: '5,5'
            }).addTo(reportMap);

            // Accuracy badge
            const badge = document.getElementById('accuracyBadge');
            badge.style.display = 'inline-block';
            if (acc <= 20) {
                badge.textContent = `± ${acc.toFixed(0)}m · Excellent`;
                badge.style.background = 'rgba(34,197,94,0.15)'; badge.style.color = '#22c55e';
            } else if (acc <= 100) {
                badge.textContent = `± ${acc.toFixed(0)}m · Good`;
                badge.style.background = 'rgba(59,130,246,0.15)'; badge.style.color = '#3b82f6';
            } else {
                badge.textContent = `± ${acc.toFixed(0)}m · Approximate`;
                badge.style.background = 'rgba(245,158,11,0.15)'; badge.style.color = '#f59e0b';
            }

            // Once accuracy is good enough, stop watching to save battery
            if (acc <= 30) {
                navigator.geolocation.clearWatch(gpsWatchId);
                clearTimeout(gpsTimeoutId);
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-crosshairs"></i> 📍 High-Accuracy GPS';
            }
        },
        (error) => {
            const msgs = {1:'Location permission denied',2:'Position unavailable',3:'Request timed out'};
            status.innerHTML = `<span style="color: var(--danger);"><i class="fas fa-times-circle"></i> ${msgs[error.code] || 'GPS error'}. Enable location in browser settings.</span>`;
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-crosshairs"></i> 📍 High-Accuracy GPS';
            clearTimeout(gpsTimeoutId);
        },
        { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
}

// ==================== ADDRESS SEARCH ====================
function searchAddress() {
    const query = document.getElementById('locationInput').value.trim();
    const status = document.getElementById('locEnhanceStatus');
    if (!query) { status.innerHTML = '<span style="color: var(--warning);">Enter an address to search</span>'; return; }

    status.innerHTML = '<span style="color: var(--accent);"><i class="fas fa-search"></i> Searching...</span>';
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`)
        .then(r => r.json())
        .then(results => {
            if (results.length > 0) {
                const r = results[0];
                const lat = parseFloat(r.lat), lng = parseFloat(r.lon);
                placeMarker(lat, lng);
                document.getElementById('locationInput').value = r.display_name;
                reportMap.setView([lat, lng], 16);
                status.innerHTML = '<span style="color: var(--success);"><i class="fas fa-check-circle"></i> Location found & pinned on map!</span>';
            } else {
                status.innerHTML = '<span style="color: var(--warning);">No results. Try a more specific address.</span>';
            }
        })
        .catch(() => {
            status.innerHTML = '<span style="color: var(--danger);">Search failed. Check your connection.</span>';
        });
}
// Allow Enter key in location input to trigger search
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('locationInput').addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); searchAddress(); }
    });
});
