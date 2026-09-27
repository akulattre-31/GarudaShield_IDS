// ══════════════════════════════════════════════════════════════════
// GARUDA KAVACH — CYBER-PHYSICAL DRONE DEFENSE SENTINEL
// Team Garuda Kavach | Tactical M5 Dashboard Client Application
// ══════════════════════════════════════════════════════════════════

// ── 1. ATTACK COLOR THEMES & SPECIFICATIONS ───────────────────────
const ATTACK_THEMES = {
    GPS_SPOOFING: {
        id: 'gps',
        name: 'GPS Spoofing',
        color: '#ff2a55',        // Neon Crimson
        bgAlpha: 'rgba(255, 42, 85, 0.15)',
        rowId: 'threat-gps',
        countermeasure: 'Inertial Position Lock & Optical Hover'
    },
    MAVLINK_FLOOD: {
        id: 'dos',
        name: 'MAVLink Rate Flood',
        color: '#ff9900',        // Vivid Amber
        bgAlpha: 'rgba(255, 153, 0, 0.15)',
        rowId: 'threat-dos',
        countermeasure: 'Kernel eBPF Packet Ingress Throttling'
    },
    COMMAND_INJECTION: {
        id: 'injection',
        name: 'Command Injection',
        color: '#a855f7',        // Electric Violet
        bgAlpha: 'rgba(168, 85, 247, 0.15)',
        rowId: 'threat-cmd',
        countermeasure: 'Cryptographic Ed25519 Auth Drop'
    },
    REPLAY_ATTACK: {
        id: 'replay',
        name: 'Replay Attack',
        color: '#00e5ff',        // Neon Electric Cyan
        bgAlpha: 'rgba(0, 240, 255, 0.15)',
        rowId: 'threat-rpl',
        countermeasure: 'Temporal Freshness Nonce Expiry'
    },
    SENSOR_ANOMALY: {
        id: 'drift',
        name: 'Sensor Drift / Anomaly',
        color: '#10b981',        // Neon Emerald
        bgAlpha: 'rgba(16, 185, 129, 0.15)',
        rowId: 'threat-drift',
        countermeasure: 'EKF Chi-Square Decoupling Failsafe'
    },
    UNMENTIONED_ATTACK: {
        id: 'unmentioned',
        name: 'Unclassified Anomaly',
        color: '#080c16',        // Tactical Obsidian Black
        accentBorder: '#ffffff',
        bgAlpha: 'rgba(8, 12, 22, 0.85)',
        rowId: null,
        countermeasure: 'Zero-Trust Protocol Isolation & Autonomous Guard'
    }
};

function resolveAttackTheme(typeStr) {
    const raw = (typeStr || '').toUpperCase().trim();
    if (raw.includes('GPS') || raw.includes('SPOOF')) return ATTACK_THEMES.GPS_SPOOFING;
    if (raw.includes('FLOOD') || raw.includes('DOS') || raw.includes('RATE')) return ATTACK_THEMES.MAVLINK_FLOOD;
    if (raw.includes('INJECTION') || raw.includes('ROGUE') || raw.includes('CMD')) return ATTACK_THEMES.COMMAND_INJECTION;
    if (raw.includes('REPLAY') || raw.includes('NONCE') || raw.includes('STALE')) return ATTACK_THEMES.REPLAY_ATTACK;
    if (raw.includes('SENSOR') || raw.includes('DRIFT') || raw.includes('ANOMALY') || raw.includes('EKF')) return ATTACK_THEMES.SENSOR_ANOMALY;
    
    // For any unmentioned/custom attack: Return Tactical Obsidian Black theme
    const formattedName = typeStr ? typeStr.replace(/_/g, ' ') : 'Unclassified Threat';
    return {
        id: 'unmentioned',
        name: formattedName,
        color: '#080c16',
        accentBorder: '#ffffff',
        bgAlpha: 'rgba(8, 12, 22, 0.85)',
        rowId: null,
        countermeasure: 'Zero-Trust Protocol Isolation & Autonomous Guard'
    };
}


// ── 3. TACTICAL LEAFLET MAP & BESIDE-DRONE 3D CUBE HUD ─────────────
// Disable scrollWheelZoom so users can scroll the page freely
const map = L.map('tactical-map', {
    zoomControl: true,
    attributionControl: false,
    scrollWheelZoom: false
}).setView([-35.363262, 149.165237], 17);

L.tileLayer('https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}', {
    maxZoom: 20,
    attribution: 'Google Satellite Hybrid'
}).addTo(map);

// Custom Drone Marker with attached 3D Holographic Coordinate Cube
const droneCustomIcon = L.divIcon({
    className: 'custom-drone-leaflet-icon',
    html: `
        <div class="drone-marker-wrap" id="drone-marker-root">
            <div class="drone-pulse" id="drone-ping-ring"></div>
            <div id="drone-svg-container" style="position:relative;width:40px;height:40px;display:flex;align-items:center;justify-content:center;transition:transform 0.3s ease;">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
                     stroke-linecap="round" stroke-linejoin="round"
                     style="color:var(--hud-threat, #00f0ff);filter:drop-shadow(0 0 8px var(--hud-threat, #00f0ff));width:34px;height:34px;">
                    <circle cx="5"  cy="5"  r="2.2"/>
                    <circle cx="19" cy="5"  r="2.2"/>
                    <circle cx="5"  cy="19" r="2.2"/>
                    <circle cx="19" cy="19" r="2.2"/>
                    <line x1="6.5"  y1="6.5"  x2="17.5" y2="17.5"/>
                    <line x1="6.5"  y1="17.5" x2="17.5" y2="6.5"/>
                    <circle cx="12" cy="12" r="3.2" fill="var(--hud-threat, #00f0ff)" fill-opacity="0.35"/>
                </svg>
            </div>
            <!-- Floating Mini 3D Glass Cube beside the Drone -->
            <div class="drone-cube-hud" id="drone-cube-hud">
                <div class="drone-cube-title">
                    <svg class="w-3 h-3 text-cyan-400 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                    <span id="cube-status-title">DRONE-01 // ACTIVE</span>
                </div>
                <div style="display:flex;justify-content:space-between;gap:8px;font-size:10px;">
                    <span style="color:#8295b5;">LAT</span>
                    <span id="cube-lat" style="color:#00f0ff;font-weight:700;">-35.363262°</span>
                </div>
                <div style="display:flex;justify-content:space-between;gap:8px;font-size:10px;">
                    <span style="color:#8295b5;">LON</span>
                    <span id="cube-lon" style="color:#00f0ff;font-weight:700;">149.165237°</span>
                </div>
                <div style="display:flex;justify-content:space-between;gap:8px;font-size:10px;border-top:1px solid rgba(255,255,255,0.08);margin-top:3px;padding-top:2px;">
                    <span style="color:#8295b5;">ALT</span>
                    <span id="cube-alt" style="color:#38bdf8;font-weight:700;">150.0m</span>
                </div>
                <div style="display:flex;justify-content:space-between;gap:8px;font-size:9px;margin-top:2px;color:#a855f7;">
                    <span style="color:#8295b5;">ZONE</span>
                    <span id="cube-zone" style="font-weight:600;">SECTOR A // CANBERRA</span>
                </div>
            </div>
        </div>
    `,
    iconSize: [44, 44],
    iconAnchor: [22, 22]
});

let droneMarker = L.marker([-35.363262, 149.165237], { icon: droneCustomIcon }).addTo(map);
let flightPath = L.polyline([], {
    color: '#00f0ff',
    weight: 2.5,
    opacity: 0.85,
    dashArray: '6,6'
}).addTo(map);

// Attack markers array: { marker, type, logIndex, timeStr, lat, lon }
let attackMarkers = [];


// ── 4. REAL-TIME MOVING ANOMALY WAVEFORM GRAPH ────────────────────
const anomalyCanvas = document.getElementById('anomalyChart');
const anomalyCtx = anomalyCanvas ? anomalyCanvas.getContext('2d') : null;

const CHART_HISTORY = 75;
const ALERT_THRESHOLD = 16.81;

let anomalyData = Array(CHART_HISTORY).fill(1.2);
let currentResidual = 1.2;
let targetResidual = 1.2;
let spikeDecayLockUntil = 0;
let anomalyChart = null;
let currentChartAlerting = false;

if (anomalyCtx) {
    const gradNominal = anomalyCtx.createLinearGradient(0, 0, 0, 140);
    gradNominal.addColorStop(0, 'rgba(0, 240, 255, 0.45)');
    gradNominal.addColorStop(1, 'rgba(0, 240, 255, 0.01)');

    anomalyChart = new Chart(anomalyCtx, {
        type: 'line',
        data: {
            labels: Array(CHART_HISTORY).fill(''),
            datasets: [
                {
                    label: 'Kinematic Residual (χ²)',
                    data: [...anomalyData],
                    borderColor: '#00f0ff',
                    backgroundColor: gradNominal,
                    borderWidth: 2.2,
                    pointRadius: 0,
                    fill: true,
                    tension: 0.38
                },
                {
                    label: 'Threshold (16.81)',
                    data: Array(CHART_HISTORY).fill(ALERT_THRESHOLD),
                    borderColor: 'rgba(255, 153, 0, 0.85)',
                    borderWidth: 1.5,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: false,
                    tension: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: { duration: 0 },
            scales: {
                y: {
                    min: 0,
                    max: 45,
                    grid: { color: 'rgba(30, 42, 66, 0.55)' },
                    ticks: {
                        color: '#8295b5',
                        font: { family: 'JetBrains Mono', size: 10 },
                        stepSize: 10
                    }
                },
                x: { display: false }
            },
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });
}

// Continuous moving waveform loop: ~10Hz smooth scrolling oscilloscope
setInterval(() => {
    if (!anomalyChart) return;

    // Smooth interpolation towards target residual
    currentResidual += (targetResidual - currentResidual) * 0.32;
    // Micro-noise for live realism
    const noise = targetResidual < 4.0 ? (Math.random() - 0.5) * 0.35 : (Math.random() - 0.5) * 0.8;
    const valueToPush = Math.max(0.4, currentResidual + noise);

    anomalyData.push(valueToPush);
    if (anomalyData.length > CHART_HISTORY) anomalyData.shift();

    const isSpiking = valueToPush >= ALERT_THRESHOLD;
    updateAnomalyChartStyle(isSpiking, valueToPush);

    anomalyChart.data.datasets[0].data = [...anomalyData];
    anomalyChart.update('none');

    // Gradual decay back to nominal baseline if not under continuous attack
    if (targetResidual > 2.2) {
        targetResidual -= 0.55;
        if (targetResidual < 1.4) targetResidual = 1.4;
    }
}, 100);

function triggerWaveformSpike(spikeValue, theme) {
    targetResidual = spikeValue || 36.5;
    currentResidual = Math.max(currentResidual, targetResidual * 0.88);
    spikeDecayLockUntil = Date.now() + 3200; // Hold spike so subsequent nominal telemetry frames do not squash it

    const card = document.getElementById('anomaly-card');
    if (card) {
        card.classList.add('chart-spike-alert');
        setTimeout(() => card.classList.remove('chart-spike-alert'), 1400);
    }
}

function updateAnomalyChartStyle(isSpiking, value) {
    if (!anomalyChart || !anomalyCtx) return;

    const statusLabel = document.getElementById('anomaly-status-label');
    const dot = document.getElementById('anomaly-dot');

    if (isSpiking !== currentChartAlerting) {
        currentChartAlerting = isSpiking;
        const color = isSpiking ? (window._activeAttackTheme?.color || '#ff2a55') : '#00f0ff';

        const grad = anomalyCtx.createLinearGradient(0, 0, 0, 140);
        if (isSpiking) {
            grad.addColorStop(0, 'rgba(255, 42, 85, 0.55)');
            grad.addColorStop(1, 'rgba(255, 42, 85, 0.02)');
        } else {
            grad.addColorStop(0, 'rgba(0, 240, 255, 0.45)');
            grad.addColorStop(1, 'rgba(0, 240, 255, 0.01)');
        }

        anomalyChart.data.datasets[0].borderColor = color;
        anomalyChart.data.datasets[0].backgroundColor = grad;

        if (statusLabel) {
            statusLabel.textContent = isSpiking
                ? `⚡ ATTACK DETECTED: SPIKE ${value.toFixed(1)} χ²`
                : 'Monitoring sensor stream…';
            statusLabel.style.color = isSpiking ? '#ff2a55' : '#00f0ff';
        }
        if (dot) {
            dot.className = isSpiking
                ? 'w-2.5 h-2.5 rounded-full bg-brand-danger animate-ping'
                : 'w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse glow-accent';
        }
    }
}


// ── 5. WEBSOCKET CONNECTION & STREAM DISCONNECTION HANDLING ────────
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/telemetry`);

let incidentLog = [];
let prevAlt = 0, prevSpd = 0;
let lastKnownLat = -35.363262;
let lastKnownLon = 149.165237;
let lastKnownAlt = 0.0;
let isStreamConnected = false;
let lastPacketTimestamp = 0;

function setDisconnectedUI() {
    isStreamConnected = false;
    const icon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');
    const subStatusText = document.getElementById('sub-status-text');
    const mapStatus = document.getElementById('map-drone-status');
    const cubeTitle = document.getElementById('cube-status-title');
    const cubeZone = document.getElementById('cube-zone');
    const cubeAlt = document.getElementById('cube-alt');
    const banner = document.getElementById('status-banner');
    const pingDot = document.getElementById('conn-ping-dot');

    if (icon) icon.className = 'w-3 h-3 bg-rose-500 rounded-full animate-pulse';
    if (statusText) {
        statusText.textContent = 'NOT CONNECTED';
        statusText.className = 'font-tech text-xs font-bold tracking-widest text-rose-400 uppercase';
    }
    if (subStatusText) {
        subStatusText.textContent = 'SIMULATOR OFFLINE';
    }
    if (pingDot) pingDot.className = 'w-2 h-2 rounded-full bg-rose-500';

    if (mapStatus) {
        mapStatus.textContent = 'SIMULATOR DISCONNECTED';
        mapStatus.className = 'text-rose-400 font-semibold font-tech tracking-wider';
    }
    if (cubeTitle) {
        cubeTitle.textContent = 'DRONE-01 // OFFLINE';
    }
    if (cubeZone) {
        cubeZone.textContent = 'STANDBY // GROUND';
        cubeZone.style.color = '#8295b5';
    }
    if (cubeAlt) {
        cubeAlt.textContent = '0.0m';
    }

    if (banner) {
        banner.style.borderBottomColor = 'rgba(244, 63, 94, 0.25)';
        banner.style.boxShadow = '';
    }
    document.body.classList.remove('critical-threat-mode');

    // Strictly 0.0 altitude and speed when drone is off
    const altVal = document.getElementById('alt-val');
    if (altVal) altVal.innerHTML = '0.0 m';
    const spdVal = document.getElementById('spd-val');
    if (spdVal) spdVal.innerHTML = '0.0 m/s';
    const latVal = document.getElementById('lat-val');
    if (latVal) latVal.textContent = '—';

    updateSegmentBar('alt-segments', 0);
    updateSegmentBar('spd-segments', 0);

    const syncBadge = document.getElementById('telemetry-sync-badge');
    if (syncBadge) {
        syncBadge.textContent = 'STANDBY';
        syncBadge.className = 'px-2 py-0.5 rounded-full bg-slate-900 border border-slate-700 text-slate-400 text-[9px] tracking-wider uppercase font-semibold';
    }
    const mavStatus = document.getElementById('mavlink-status');
    if (mavStatus) {
        mavStatus.textContent = 'IDLE';
        mavStatus.className = 'text-slate-400 font-semibold';
    }
}

function setConnectedUI(tel) {
    isStreamConnected = true;
    const icon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');
    const subStatusText = document.getElementById('sub-status-text');
    const mapStatus = document.getElementById('map-drone-status');
    const cubeTitle = document.getElementById('cube-status-title');
    const pingDot = document.getElementById('conn-ping-dot');

    if (icon) icon.className = 'w-3 h-3 bg-emerald-400 rounded-full animate-pulse shadow-[0_0_8px_#10b981]';
    if (statusText) {
        statusText.textContent = 'CONNECTED';
        statusText.className = 'font-tech text-xs font-bold tracking-widest text-emerald-400 uppercase';
    }
    if (subStatusText) {
        subStatusText.textContent = 'SIMULATOR ONLINE';
    }
    if (pingDot) pingDot.className = 'w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#10b981]';

    if (mapStatus) {
        mapStatus.textContent = 'AIRBORNE ACTIVE';
        mapStatus.className = 'text-cyan-300 font-semibold font-tech tracking-wider';
    }
    if (cubeTitle) {
        cubeTitle.textContent = 'DRONE-01 // LIVE';
    }

    const syncBadge = document.getElementById('telemetry-sync-badge');
    if (syncBadge) {
        syncBadge.textContent = 'TELEMETRY SYNCED';
        syncBadge.className = 'px-2 py-0.5 rounded-full bg-emerald-950/70 border border-emerald-500/40 text-emerald-400 text-[9px] tracking-wider uppercase font-semibold';
    }
    const mavStatus = document.getElementById('mavlink-status');
    if (mavStatus) {
        mavStatus.textContent = 'STREAMING';
        mavStatus.className = 'text-emerald-400 font-semibold';
    }
}

// Client-Side Watchdog: Auto-detect simulator disconnect without needing page refresh!
setInterval(() => {
    if (Date.now() - lastPacketTimestamp > 2500 && isStreamConnected) {
        setDisconnectedUI();
    }
}, 800);

ws.onopen = function() {
    console.log('[Garuda Kavach] WebSocket connected to IDS bridge');
};

ws.onmessage = function(event) {
    let data;
    try {
        data = JSON.parse(event.data);
    } catch (err) {
        console.error('Error parsing telemetry payload:', err);
        return;
    }

    // Handle operator command confirmations
    if (data.command_confirmation) {
        const conf = data.command_confirmation;
        const color = conf.action === 'FORCE_BRAKE' ? '#00f0ff' : '#ff2a55';
        showOperatorToast(conf.message, color);
        return;
    }

    const tel = data.telemetry || {};
    const linkConnected = Boolean(data.link_connected && data.system_status !== 'LINK_SEVERED');

    if (linkConnected) {
        lastPacketTimestamp = Date.now();
        setConnectedUI(tel);
    } else {
        setDisconnectedUI();
    }

    // ── Update Coordinates ──
    const lat = tel.latitude !== undefined ? tel.latitude : lastKnownLat;
    const lon = tel.longitude !== undefined ? tel.longitude : lastKnownLon;
    // When offline, altitude is strictly 0.0m
    const alt = linkConnected ? (tel.altitude_m !== undefined ? tel.altitude_m : 0.0) : 0.0;
    const spd = linkConnected ? (tel.speed_ms !== undefined ? tel.speed_ms : 0.0) : 0.0;

    lastKnownLat = lat;
    lastKnownLon = lon;
    lastKnownAlt = alt;

    // ── Update Beside-Drone 3D Cube HUD ──
    const cubeLat = document.getElementById('cube-lat');
    const cubeLon = document.getElementById('cube-lon');
    const cubeAlt = document.getElementById('cube-alt');
    if (cubeLat) cubeLat.textContent = `${lat.toFixed(6)}°`;
    if (cubeLon) cubeLon.textContent = `${lon.toFixed(6)}°`;
    if (cubeAlt) cubeAlt.textContent = `${alt.toFixed(1)}m`;

    // ── Move Drone Marker & Flight Path on Map ──
    if (lat !== 0 && lon !== 0) {
        droneMarker.setLatLng([lat, lon]);

        // Only add to trail if actively streaming and moved
        if (linkConnected && (tel.speed_ms || 0) > 0.1) {
            flightPath.addLatLng([lat, lon]);
            const coords = flightPath.getLatLngs();
            if (coords.length > 1200) {
                coords.shift();
                flightPath.setLatLngs(coords);
            }
        }

        // Camera follow
        if (!window._panCounter) window._panCounter = 0;
        if (window._panCounter++ % 10 === 0 && linkConnected) {
            map.panTo([lat, lon], { animate: true, duration: 0.8 });
        }
    }

    // Drone Orientation / Heading
    const vx = tel.vx !== undefined ? tel.vx : 0;
    const vy = tel.vy !== undefined ? tel.vy : 0;
    const headingDeg = Math.atan2(vy, vx) * (180 / Math.PI);
    const svgBox = document.getElementById('drone-svg-container');
    if (svgBox && (vx !== 0 || vy !== 0)) {
        svgBox.style.transform = `rotate(${headingDeg}deg)`;
    }

    // ── Flight Telemetry Panel ──
    const altTrend = alt > prevAlt ? '▲' : alt < prevAlt ? '▼' : '';
    const spdTrend = spd > prevSpd ? '▲' : spd < prevSpd ? '▼' : '';
    prevAlt = alt;
    prevSpd = spd;

    const altVal = document.getElementById('alt-val');
    if (altVal) {
        altVal.innerHTML = linkConnected ? `<span class="text-cyan-400 text-xs">${altTrend}</span> ${alt.toFixed(1)} m` : '0.0 m';
    }

    const spdVal = document.getElementById('spd-val');
    if (spdVal) {
        spdVal.innerHTML = linkConnected ? `<span class="text-cyan-400 text-xs">${spdTrend}</span> ${spd.toFixed(1)} m/s` : '0.0 m/s';
    }

    const latVal = document.getElementById('lat-val');
    if (latVal) {
        latVal.textContent = linkConnected ? (tel.latency_ms || 12) : '—';
    }

    if (linkConnected) {
        updateSegmentBar('alt-segments', Math.min((alt / 200) * 100, 100));
        updateSegmentBar('spd-segments', Math.min((spd / 25) * 100, 100));
    } else {
        updateSegmentBar('alt-segments', 0);
        updateSegmentBar('spd-segments', 0);
    }

    // ── Avionics Health ──
    const cpuVal = tel.cpu_load_pct !== undefined ? tel.cpu_load_pct : (linkConnected ? 20 : 0);
    const ramVal = tel.ram_load_pct !== undefined ? tel.ram_load_pct : (linkConnected ? 35 : 0);

    const cpuTxt = document.getElementById('cpu-val-text');
    if (cpuTxt) cpuTxt.textContent = `${cpuVal.toFixed(0)}%`;
    const cpuFill = document.getElementById('cpu-fill');
    if (cpuFill) cpuFill.style.width = `${Math.min(Math.max(cpuVal, 0), 100)}%`;

    const ramTxt = document.getElementById('ram-val-text');
    const ramFill = document.getElementById('ram-fill');
    if (ramTxt) ramTxt.textContent = `${ramVal.toFixed(0)}%`;
    if (ramFill) ramFill.style.width = `${ramVal}%`;

    // ── Kinematic Residual & Anomaly Graph ──
    const residual = data.kinematic_residual !== undefined ? data.kinematic_residual : 1.2;
    if (data.new_incident || residual > ALERT_THRESHOLD) {
        const attackType = (data.incident_details && data.incident_details.type) || 'GPS_SPOOFING';
        const theme = resolveAttackTheme(attackType);
        window._activeAttackTheme = theme;
        triggerWaveformSpike(residual, theme);
    } else {
        if (Date.now() > spikeDecayLockUntil) {
            targetResidual = Math.max(1.1, residual);
        }
    }

    // ── Threat State & Banner Management ──
    if (data.system_status && data.system_status !== 'LINK_SEVERED') {
        handleThreatState(data.system_status, data.incident_details);
    }

    // ── Incident Logging & Map Dots ──
    if (data.new_incident && data.incident_details) {
        recordIncident(data.incident_details, lat, lon);
    }
};

ws.onclose = function() {
    console.warn('[Garuda Kavach] Telemetry WebSocket connection closed');
    setDisconnectedUI();
};


// ── 6. THREAT MATRIX DYNAMICS & ATTACK STYLING ─────────────────────
let activeThreatTimer = null;

function handleThreatState(status, incidentDetails) {
    const banner = document.getElementById('status-banner');
    const icon = document.getElementById('status-icon');
    const txt = document.getElementById('status-text');
    const droneCube = document.getElementById('drone-cube-hud');

    if (status === 'NOMINAL' || status === 'STREAM_ACTIVE') {
        window._activeThreat = 'NOMINAL';
        window._activeAttackTheme = null;

        // Reset Threat Cards
        Object.values(ATTACK_THEMES).forEach(theme => {
            const row = document.getElementById(theme.rowId);
            if (row) {
                row.classList.remove('active-threat');
                const badge = row.querySelector('.threat-badge-alert, .threat-badge-safe');
                if (badge) {
                    badge.className = 'threat-badge-safe';
                    badge.textContent = 'Clear';
                    badge.style.color = '';
                    badge.style.borderColor = '';
                }
            }
        });

        if (droneCube) droneCube.classList.remove('cube-alert');

        if (banner) {
            banner.style.borderBottomColor = 'rgba(0, 240, 255, 0.16)';
            banner.style.boxShadow = '';
        }
        if (icon) icon.className = 'w-3.5 h-3.5 bg-brand-accent rounded-full animate-pulse glow-accent';
        if (txt) {
            txt.textContent = 'Sentinel Shield Online';
            txt.style.color = '#67e8f9';
        }

        document.documentElement.style.setProperty('--hud-threat', '#00f0ff');
        flightPath.setStyle({ color: '#00f0ff' });
        document.body.classList.remove('critical-threat-mode');

        // Reset Threat Metrics
        const mgps = document.getElementById('metric-gps');
        const mdos = document.getElementById('metric-dos');
        const mcmd = document.getElementById('metric-cmd');
        const mrpl = document.getElementById('metric-rpl');
        const mdrift = document.getElementById('metric-drift');
        if (mgps) mgps.innerHTML = 'χ² 1.2 // EKF Locked';
        if (mdos) mdos.innerHTML = '22 pkt/s // Clean';
        if (mcmd) mcmd.innerHTML = '0 Rejected // Active';
        if (mrpl) mrpl.innerHTML = '&lt;40ms // Fresh';
        if (mdrift) mdrift.innerHTML = '0.03m // Decoupled: No';

        const mapStatus = document.getElementById('map-drone-status');
        if (mapStatus) {
            mapStatus.textContent = isStreamConnected ? 'PATROLLING SECTOR A' : 'STREAM INACTIVE — DRONE STATIONARY';
            mapStatus.className = isStreamConnected ? 'text-cyan-300 font-semibold' : 'text-amber-400 font-semibold';
            mapStatus.style.color = '';
        }
        return;
    }

    // ── Threat Detected State ──
    const attackType = (incidentDetails && incidentDetails.type) || status;
    const theme = resolveAttackTheme(attackType);
    window._activeAttackTheme = theme;
    window._activeThreat = status;

    // Highlight the specific threat card in the Threat Matrix
    const activeRow = document.getElementById(theme.rowId);
    if (activeRow) {
        activeRow.classList.add('active-threat');
        const badge = activeRow.querySelector('.threat-badge-safe, .threat-badge-alert');
        if (badge) {
            badge.className = 'threat-badge-alert';
            badge.textContent = 'INTERCEPTED';
            badge.style.color = theme.color;
            badge.style.borderColor = theme.color;
        }
    }

    if (droneCube) droneCube.classList.add('cube-alert');

    // Dynamic color on banner, map trail, and drone marker
    document.documentElement.style.setProperty('--hud-threat', theme.color);
    flightPath.setStyle({ color: theme.color });

    if (banner) {
        banner.style.borderBottomColor = theme.color;
        banner.style.boxShadow = `0 4px 28px ${theme.color}40`;
    }
    if (icon) {
        icon.className = 'w-3.5 h-3.5 rounded-full animate-ping';
        icon.style.backgroundColor = theme.color;
    }
    if (txt) {
        txt.textContent = `ALERT // ${theme.name.toUpperCase()} INTERCEPTED`;
        txt.style.color = theme.color;
    }

    const mapStatus = document.getElementById('map-drone-status');
    if (mapStatus) {
        mapStatus.textContent = `DEFENSE ENGAGED: ${theme.name.toUpperCase()}`;
        mapStatus.className = 'font-bold tracking-wider';
        mapStatus.style.color = theme.color;
    }

    document.body.classList.add('critical-threat-mode');
    if (activeThreatTimer) clearTimeout(activeThreatTimer);
    activeThreatTimer = setTimeout(() => {
        document.body.classList.remove('critical-threat-mode');
    }, 1400);
}


// ── 7. INCIDENT RECORDING & MAP DOT RETENTION RULES ────────────────
// RETENTION SPECIFICATION:
// 1. Same attack type: keep ONLY the past 5 recorded dots on the map.
// 2. Across all different attacks: retain at most 10 total dots on the map.
function recordIncident(details, lat, lon) {
    const tbody = document.getElementById('ledger-body');
    if (!tbody) return;

    const theme = resolveAttackTheme(details.type);
    const logIndexNum = incidentLog.length + 1;
    const logIndex = String(logIndexNum).padStart(2, '0');

    // Human local timestamp (NO robotic Zulu)
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;

    const confPct = details.confidence !== undefined
        ? `${(details.confidence * 100).toFixed(0)}%`
        : '96%';

    const hash = '0x' + btoa(`${details.type}${Date.now()}`).slice(0, 10).toLowerCase();
    const failsafeMode = details.failsafe_mode || (theme.id === 'gps' || theme.id === 'injection' ? 'BRAKE' : (theme.id === 'drift' ? 'LAND' : 'RTL'));

    // Increment counter & update status in Threat Matrix
    const rowEl = document.getElementById(theme.rowId);
    if (rowEl) {
        const counterEl = rowEl.querySelector('.event-counter');
        const curCount = parseInt(rowEl.dataset.count || '0', 10) + 1;
        rowEl.dataset.count = curCount;
        if (counterEl) {
            counterEl.innerHTML = `<span style="color:${theme.color};font-weight:700;">Report #${logIndex}</span> (${curCount} logged)`;
        }
    }

    // Update dynamic metric preview on that threat card
    const metricEl = document.getElementById(`metric-${theme.id}`);
    if (metricEl) {
        if (theme.id === 'gps') metricEl.innerHTML = `<span style="color:#ff2a55;font-weight:700;">χ² ${(currentResidual || 36.8).toFixed(1)} // SPIKE DETECTED</span>`;
        if (theme.id === 'dos') metricEl.innerHTML = `<span style="color:#ff9900;font-weight:700;">480 pkt/s // FLOOD INGRESS</span>`;
        if (theme.id === 'injection') metricEl.innerHTML = `<span style="color:#a855f7;font-weight:700;">INVALID SIG // REJECTED</span>`;
        if (theme.id === 'replay') metricEl.innerHTML = `<span style="color:#00e5ff;font-weight:700;">STALE NONCE // DISCARDED</span>`;
        if (theme.id === 'drift') metricEl.innerHTML = `<span style="color:#10b981;font-weight:700;">Δ 14.2m // EKF DECOUPLED</span>`;
    }

    // ── Drop Colored Glowing Attack Dot Marker on Leaflet Map ──
    let mapMarkerObj = null;
    let dropLat = (lat !== undefined && lat !== null && !isNaN(lat)) ? lat : lastKnownLat;
    let dropLon = (lon !== undefined && lon !== null && !isNaN(lon)) ? lon : lastKnownLon;

    // Tactical spatial distribution for stationary/simulated bursts so multiple dots don't stack on exact same pixel
    if (attackMarkers.some(m => Math.abs(m.lat - dropLat) < 0.00003 && Math.abs(m.lon - dropLon) < 0.00003)) {
        const angle = (logIndexNum * 137.5) * (Math.PI / 180);
        const radiusDeg = 0.00022 + (logIndexNum % 5) * 0.00007;
        dropLat = dropLat + Math.sin(angle) * radiusDeg;
        dropLon = dropLon + Math.cos(angle) * radiusDeg;
    }

    const isDark = (theme.color === '#080c16' || theme.id === 'unmentioned');
    const beaconColor = isDark ? '#ffffff' : theme.color;
    const coreBg = isDark ? '#080c16' : theme.color;
    const coreBorder = isDark ? '2px solid #ffffff' : '2px solid #ffffff';
    const coreShadow = isDark ? '0 0 12px #ffffff' : `0 0 10px ${theme.color}`;

    const dotHtml = `
        <div style="position:relative;width:24px;height:24px;display:flex;align-items:center;justify-content:center;">
            <div style="position:absolute;width:100%;height:100%;border-radius:50%;background:${beaconColor};opacity:0.75;animation:attack-beacon 1.8s ease-out infinite;"></div>
            <div style="width:13px;height:13px;border-radius:50%;background:${coreBg};border:${coreBorder};box-shadow:${coreShadow};z-index:2;"></div>
        </div>
    `;
    const dotIcon = L.divIcon({
        className: 'attack-marker-glow',
        html: dotHtml,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });

    const popupHtml = `
        <div class="attack-popup-card">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.1);padding-bottom:4px;">
                <span class="report-pill" style="color:${isDark ? '#38bdf8' : theme.color};border-color:${isDark ? '#38bdf8' : theme.color}50;background:${isDark ? '#38bdf8' : theme.color}20">
                    REPORT #${logIndex}
                </span>
                <span style="font-size:10px;color:#94a3b8;font-family:'JetBrains Mono',monospace;">${timeStr} Local</span>
            </div>
            <div style="font-weight:800;color:${isDark ? '#ffffff' : theme.color};font-size:12px;margin-bottom:4px;font-family:'Rajdhani','Space Grotesk',sans-serif;letter-spacing:0.04em;">
                ${theme.name.toUpperCase()}
            </div>
            <div style="font-size:11px;color:#cbd5e1;line-height:1.5;">
                <div><strong>Confidence:</strong> <span style="color:#00f0ff;">${confPct}</span></div>
                <div><strong>Countermeasure:</strong> ${theme.countermeasure}</div>
                <div><strong>Auto Failsafe:</strong> <span style="color:#34d399;font-weight:700;">${failsafeMode}</span></div>
                <div><strong>Log Evidence:</strong> Saved as Forensic Incident Report #${logIndex}</div>
                <div style="margin-top:4px;padding:3px 6px;border-radius:6px;background:rgba(255,255,255,0.04);font-size:9.5px;color:#94a3b8;font-family:'JetBrains Mono',monospace;">
                    ${dropLat.toFixed(6)}°, ${dropLon.toFixed(6)}°
                </div>
            </div>
        </div>
    `;

    const marker = L.marker([dropLat, dropLon], { icon: dotIcon }).addTo(map);
    marker.bindPopup(popupHtml);

    // Hover Tooltip: Instantly shows Log No and Attack Name on cursor hover
    marker.bindTooltip(`
        <div style="font-family:'Rajdhani','Space Grotesk',sans-serif;font-size:11px;font-weight:700;color:${isDark ? '#38bdf8' : theme.color};letter-spacing:0.04em;">
            Report #${logIndex} &bull; ${theme.name}
        </div>
    `, {
        permanent: false,
        direction: 'top',
        className: 'tactical-map-tooltip',
        offset: [0, -10]
    });

    mapMarkerObj = {
        marker,
        type: theme.id,
        typeName: theme.name,
        logIndex,
        lat: dropLat,
        lon: dropLon,
        popupHtml
    };

    // ── ENFORCE STRICT RETENTION RULES ──
    // 1. Same attack type: keep ONLY past 5 recorded on the map
    const sameTypeMarkers = attackMarkers.filter(m => m.type === theme.id);
    if (sameTypeMarkers.length >= 5) {
        const oldestOfType = sameTypeMarkers[0];
        map.removeLayer(oldestOfType.marker);
        attackMarkers = attackMarkers.filter(m => m !== oldestOfType);
    }

    // 2. Across all different attacks: retain at most 10 total on the map
    if (attackMarkers.length >= 10) {
        const oldestOverall = attackMarkers.shift();
        map.removeLayer(oldestOverall.marker);
    }

    attackMarkers.push(mapMarkerObj);

    // Update Forensics Summary counter in Matrix
    const summaryTotalEl = document.getElementById('matrix-total-reports');
    if (summaryTotalEl) {
        summaryTotalEl.textContent = `${logIndexNum} Logged (${attackMarkers.length} on Map)`;
    }

    // ── Add to Forensic Incident Ledger Table ──
    const row = document.createElement('tr');
    row.className = 'hover:bg-slate-800/40 transition-colors cursor-pointer group';
    row.innerHTML = `
        <td class="py-2.5 px-3 text-cyan-300 font-bold">Report #${logIndex}</td>
        <td class="py-2.5 px-3 text-brand-muted font-mono">${timeStr}</td>
        <td class="py-2.5 px-3 font-semibold" style="color: ${theme.color}">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background-color:${theme.color};margin-right:6px;box-shadow:0 0 6px ${theme.color};"></span>
            ${theme.name} <span class="text-[10px] text-brand-muted">(${confPct})</span>
        </td>
        <td class="py-2.5 px-3 text-slate-300">
            <span>${theme.countermeasure}</span>
            <span class="ml-1.5 px-1.5 py-0.5 rounded text-[9px] bg-slate-800 border border-slate-700 text-emerald-400 font-bold">${failsafeMode}</span>
        </td>
        <td class="py-2.5 px-3 font-mono text-[9px] text-cyan-400/80 truncate max-w-[90px]">${hash}</td>
    `;

    // Clicking row centers map on that attack's dot & opens popup
    row.addEventListener('click', () => {
        map.flyTo([dropLat, dropLon], 18, { animate: true, duration: 0.8 });
        if (map.hasLayer(marker)) {
            marker.openPopup();
        } else {
            L.popup()
                .setLatLng([dropLat, dropLon])
                .setContent(popupHtml)
                .openOn(map);
        }
    });

    tbody.prepend(row);

    // Keep visible ledger entries tidy (max 10 rows in view)
    while (tbody.children.length > 10) {
        tbody.removeChild(tbody.lastChild);
    }

    // Save to memory ledger
    incidentLog.push({
        id: logIndex,
        timestamp: timeStr,
        type: theme.name,
        confidence: confPct,
        action: theme.countermeasure,
        failsafe_mode: failsafeMode,
        hash,
        coordinates: { lat: dropLat, lon: dropLon }
    });
}


// ── 8. EMERGENCY COUNTERMEASURES & COOL TOAST/BANNER FEEDBACK ─────
const brakeBtn = document.querySelector('.btn-brake');
if (brakeBtn) {
    brakeBtn.addEventListener('click', () => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'FORCE_BRAKE' }));
            showOperatorToast(
                '⚡ AIRBORNE BRAKE ENGAGED — Zero-velocity position lock commanded to flight autopilot via secure channel.',
                '#00f0ff'
            );
            updateBannerNotice('COUNTERMEASURE DISPATCHED: AIRBORNE BRAKE HOVER LOCK', '#00f0ff');
        } else {
            showOperatorToast('WebSocket disconnected — Cannot dispatch airborne brake.', '#ff2a55');
        }
    });
}

const rtlBtn = document.querySelector('.btn-rtl');
if (rtlBtn) {
    rtlBtn.addEventListener('click', () => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'FORCE_RTL' }));
            showOperatorToast(
                '🛡️ AUTONOMOUS RTL ACTIVATED — Inertial recall failsafe engaged. Autopilot commanded to return to launch waypoint.',
                '#ff2a55'
            );
            updateBannerNotice('COUNTERMEASURE DISPATCHED: AUTONOMOUS RETURN TO BASE', '#ff2a55');
        } else {
            showOperatorToast('WebSocket disconnected — Cannot dispatch RTL recall.', '#ff2a55');
        }
    });
}

function updateBannerNotice(msg, color) {
    const txt = document.getElementById('status-text');
    if (!txt) return;
    const prev = txt.textContent;
    const prevColor = txt.style.color;
    txt.textContent = msg;
    txt.style.color = color;
    setTimeout(() => {
        txt.textContent = prev;
        txt.style.color = prevColor;
    }, 4500);
}

// Forensic Ledger JSON Export
const exportBtn = document.getElementById('export-btn');
if (exportBtn) {
    exportBtn.addEventListener('click', () => {
        if (!incidentLog.length) {
            showOperatorToast('No forensic incidents logged yet.', '#ff9900');
            return;
        }
        const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(incidentLog, null, 2));
        const a = document.createElement('a');
        a.href = dataStr;
        a.download = `garuda_kavach_forensics_${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showOperatorToast('Forensic incident ledger exported successfully as JSON.', '#10b981');
    });
}


// ── 9. TEST SPIKE SIMULATORS (For Operator Evaluation) ────────────
document.querySelectorAll('.test-threat-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const attackKey = btn.dataset.attack || 'GPS_SPOOFING';
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: 'SIMULATE_ATTACK', type: attackKey }));
        } else {
            // Local simulation fallback if offline
            const theme = resolveAttackTheme(attackKey);
            triggerWaveformSpike(36.8, theme);
            recordIncident({
                type: attackKey,
                confidence: 0.98,
                source: 'Operator Test Console'
            }, lastKnownLat, lastKnownLon);
            handleThreatState(`CRITICAL THREAT INTERCEPTED: ${attackKey}`, { type: attackKey, confidence: 0.98 });
        }
    });
});


// ── 10. UI HELPER UTILITIES ───────────────────────────────────────
function updateSegmentBar(elementId, pct) {
    const container = document.getElementById(elementId);
    if (!container) return;
    const segments = container.querySelectorAll('div');
    const activeCount = Math.floor((pct / 100) * segments.length);
    segments.forEach((seg, idx) => {
        seg.className = idx < activeCount
            ? 'h-full w-full bg-brand-accent rounded-full transition-colors'
            : 'h-full w-full bg-slate-700/60 rounded-full transition-colors';
    });
}

function updateCpuGraph(cpuPct) {
    const segContainer = document.getElementById('cpu-segments');
    if (!segContainer) return;
    const cols = Array.from(segContainer.children);
    const active = Math.floor((cpuPct / 100) * cols.length);
    cols.forEach((col, idx) => {
        const inner = col.firstElementChild;
        if (!inner) return;
        const heights = [40, 55, 30, 80, 45, 25, 65, 40];
        const h = heights[idx] || 50;
        const colorClass = idx < active
            ? (cpuPct > 80 ? 'bg-rose-500' : 'bg-brand-accent')
            : 'bg-slate-700/40';
        inner.className = `w-full ${colorClass} transition-all duration-300`;
        inner.style.height = `${h}%`;
    });
}

// RF Spectrum Animation Loop
function animateRfSpectrum() {
    const bars = document.querySelectorAll('#rf-spectrum-bars div');
    const isThreat = window._activeThreat && window._activeThreat !== 'NOMINAL';
    bars.forEach((bar, i) => {
        const minH = (i === 4 && isThreat) ? 80 : 15;
        const maxH = (i === 4 && isThreat) ? 100 : 70;
        const randH = Math.floor(Math.random() * (maxH - minH + 1)) + minH;
        bar.style.height = `${randH}%`;
        bar.style.transition = 'height 0.3s ease';
    });
}
setInterval(animateRfSpectrum, 280);

// Sleek Liquid Glassmorphic Toast Notification Stacker
function showOperatorToast(message, color) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = 'operator-toast';
    toast.style.setProperty('--toast-color', color || '#00f0ff');
    toast.style.setProperty('--toast-glow', `${color || '#00f0ff'}40`);
    toast.innerHTML = `
        <span class="material-symbols-outlined text-[20px] shrink-0" style="color:${color || '#00f0ff'}">verified</span>
        <span class="text-xs font-mono text-white leading-snug">${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(12px) scale(0.95)';
        setTimeout(() => toast.remove(), 350);
    }, 4500);
}
