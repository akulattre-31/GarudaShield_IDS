// ══════════════════════════════════════════════════════════════════
// GARUDA KAVACH — CYBER-PHYSICAL DRONE DEFENSE SENTINEL
// Team Garuda Kavach | Tactical M5 Dashboard Client Application
// ══════════════════════════════════════════════════════════════════

// ── 1. HUMAN LOCAL CLOCK (Clean, Non-Robotic, NO Zulu) ────────────
function updateLocalClock() {
    const clockEl = document.getElementById('local-clock');
    const tzEl = document.getElementById('local-tz');
    if (!clockEl) return;

    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');
    clockEl.textContent = `${hours}:${minutes}:${seconds}`;

    if (tzEl) {
        try {
            const tzName = Intl.DateTimeFormat().resolvedOptions().timeZone.split('/').pop().replace('_', ' ');
            tzEl.textContent = tzName.toUpperCase();
        } catch (e) {
            tzEl.textContent = 'LOCAL';
        }
    }
}
updateLocalClock();
setInterval(updateLocalClock, 1000);


// ── 2. ATTACK COLOR THEMES & SPECIFICATIONS ───────────────────────
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
    }
};

function resolveAttackTheme(typeStr) {
    const raw = (typeStr || '').toUpperCase();
    if (raw.includes('GPS') || raw.includes('SPOOF')) return ATTACK_THEMES.GPS_SPOOFING;
    if (raw.includes('FLOOD') || raw.includes('DOS') || raw.includes('RATE')) return ATTACK_THEMES.MAVLINK_FLOOD;
    if (raw.includes('INJECTION') || raw.includes('ROGUE') || raw.includes('CMD')) return ATTACK_THEMES.COMMAND_INJECTION;
    if (raw.includes('REPLAY') || raw.includes('NONCE') || raw.includes('STALE')) return ATTACK_THEMES.REPLAY_ATTACK;
    if (raw.includes('SENSOR') || raw.includes('DRIFT') || raw.includes('ANOMALY') || raw.includes('EKF')) return ATTACK_THEMES.SENSOR_ANOMALY;
    return ATTACK_THEMES.GPS_SPOOFING;
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
                    <span class="drone-cube-dot"></span>
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
    targetResidual = spikeValue || 34.5;
    currentResidual = Math.max(currentResidual, targetResidual * 0.85);

    const card = document.getElementById('anomaly-card');
    if (card) {
        card.classList.add('chart-spike-alert');
        setTimeout(() => card.classList.remove('chart-spike-alert'), 1200);
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
let lastKnownAlt = 150.0;
let isStreamConnected = false;

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
    const linkConnected = data.link_connected !== undefined ? data.link_connected : true;
    isStreamConnected = linkConnected;

    // ── Update Connection Link Status in Header ──
    const banner = document.getElementById('status-banner');
    const icon = document.getElementById('status-icon');
    const statusText = document.getElementById('status-text');
    const subStatusText = document.getElementById('sub-status-text');
    const mapStatus = document.getElementById('map-drone-status');
    const cubeTitle = document.getElementById('cube-status-title');

    if (!linkConnected || data.system_status === 'LINK_SEVERED') {
        // Stream disconnected / waiting for Blue Team: Stop drone and show status!
        if (icon) icon.className = 'w-3.5 h-3.5 bg-amber-400 rounded-full animate-pulse';
        if (statusText) {
            statusText.textContent = 'TELEMETRY LINK SEVERED // WAITING FOR INGRESS';
            statusText.style.color = '#ff9900';
        }
        if (subStatusText) {
            subStatusText.textContent = 'Awaiting verified 20Hz packets on UDP 9000...';
        }
        if (mapStatus) {
            mapStatus.textContent = 'STREAM INACTIVE — DRONE STATIONARY';
            mapStatus.className = 'text-amber-400 font-semibold';
        }
        if (cubeTitle) {
            cubeTitle.textContent = 'DRONE-01 // STATIONARY';
        }

        const spdVal = document.getElementById('spd-val');
        if (spdVal) spdVal.innerHTML = '0.0 m/s';
        updateSegmentBar('spd-segments', 0);
    } else if (data.system_status === 'NOMINAL' || data.system_status === 'STREAM_ACTIVE') {
        if (icon) icon.className = 'w-3.5 h-3.5 bg-brand-accent rounded-full animate-pulse glow-accent';
        if (statusText) {
            statusText.textContent = 'Sentinel Shield Online';
            statusText.style.color = '#67e8f9';
        }
        if (subStatusText) {
            subStatusText.textContent = 'Ingress Port 9000 // Verified HMAC UDP';
        }
        if (mapStatus) {
            mapStatus.textContent = 'PATROLLING SECTOR A';
            mapStatus.className = 'text-cyan-300 font-semibold';
        }
        if (cubeTitle) {
            cubeTitle.textContent = 'DRONE-01 // ACTIVE';
        }
    }

    // ── Update Coordinates ──
    const lat = tel.latitude !== undefined ? tel.latitude : lastKnownLat;
    const lon = tel.longitude !== undefined ? tel.longitude : lastKnownLon;
    const alt = tel.altitude_m !== undefined ? tel.altitude_m : lastKnownAlt;
    const spd = linkConnected ? (tel.speed_ms !== undefined ? tel.speed_ms : prevSpd) : 0.0;

    lastKnownLat = lat;
    lastKnownLon = lon;
    lastKnownAlt = alt;

    // ── Update Corner HUD Overlay on the Map ──
    const latDisp = document.getElementById('lat-display');
    const lonDisp = document.getElementById('lon-display');
    const altDisp = document.getElementById('map-alt-hud');
    if (latDisp) latDisp.textContent = `${lat.toFixed(6)}°`;
    if (lonDisp) lonDisp.textContent = `${lon.toFixed(6)}°`;
    if (altDisp) altDisp.textContent = `${alt.toFixed(1)}m`;

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
    if (altVal) altVal.innerHTML = `<span class="text-cyan-400 text-xs">${altTrend}</span> ${alt.toFixed(1)} m`;

    const spdVal = document.getElementById('spd-val');
    if (spdVal && linkConnected) {
        spdVal.innerHTML = `<span class="text-cyan-400 text-xs">${spdTrend}</span> ${spd.toFixed(1)} m/s`;
    }

    if (tel.latency_ms !== undefined) {
        const latVal = document.getElementById('lat-val');
        if (latVal) latVal.textContent = tel.latency_ms;
    }

    updateSegmentBar('alt-segments', Math.min((alt / 200) * 100, 100));
    if (linkConnected) {
        updateSegmentBar('spd-segments', Math.min((spd / 25) * 100, 100));
    }

    // ── Avionics Health ──
    if (tel.cpu_load_pct !== undefined) {
        const cpuTxt = document.getElementById('cpu-val-text');
        if (cpuTxt) cpuTxt.textContent = `${tel.cpu_load_pct.toFixed(0)}%`;
        updateCpuGraph(tel.cpu_load_pct);
    }
    if (tel.ram_load_pct !== undefined) {
        const ramTxt = document.getElementById('ram-val-text');
        const ramFill = document.getElementById('ram-fill');
        if (ramTxt) ramTxt.textContent = `${tel.ram_load_pct.toFixed(0)}%`;
        if (ramFill) ramFill.style.width = `${tel.ram_load_pct}%`;
    }

    // ── Kinematic Residual & Anomaly Graph ──
    const residual = data.kinematic_residual !== undefined ? data.kinematic_residual : 1.2;
    if (data.new_incident || residual > ALERT_THRESHOLD) {
        const attackType = (data.incident_details && data.incident_details.type) || 'GPS_SPOOFING';
        const theme = resolveAttackTheme(attackType);
        window._activeAttackTheme = theme;
        triggerWaveformSpike(residual, theme);
    } else {
        targetResidual = Math.max(1.1, residual);
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
    const icon = document.getElementById('status-icon');
    const txt = document.getElementById('status-text');
    if (icon) icon.className = 'w-3.5 h-3.5 bg-brand-danger rounded-full animate-ping';
    if (txt) {
        txt.textContent = 'IDS BRIDGE DISCONNECTED';
        txt.style.color = '#ff2a55';
    }
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

    // Increment counter in Threat Matrix
    const rowEl = document.getElementById(theme.rowId);
    if (rowEl) {
        const counterEl = rowEl.querySelector('.event-counter');
        if (counterEl) {
            const curCount = parseInt(rowEl.dataset.count || '0', 10) + 1;
            rowEl.dataset.count = curCount;
            counterEl.textContent = `${curCount} incident${curCount > 1 ? 's' : ''} logged`;
        }
    }

    // ── Drop Colored Glowing Attack Dot Marker on Leaflet Map ──
    let mapMarkerObj = null;
    if (lat && lon) {
        const dotHtml = `
            <div style="position:relative;width:22px;height:22px;display:flex;align-items:center;justify-content:center;">
                <div style="position:absolute;width:100%;height:100%;border-radius:50%;background:${theme.color};opacity:0.6;animation:attack-beacon 1.8s ease-out infinite;"></div>
                <div style="width:13px;height:13px;border-radius:50%;background:${theme.color};border:2px solid #ffffff;box-shadow:0 0 10px ${theme.color};z-index:2;"></div>
            </div>
        `;
        const dotIcon = L.divIcon({
            className: 'attack-marker-glow',
            html: dotHtml,
            iconSize: [22, 22],
            iconAnchor: [11, 11]
        });

        const marker = L.marker([lat, lon], { icon: dotIcon }).addTo(map);
        marker.bindPopup(`
            <div style="font-family:'Plus Jakarta Sans',sans-serif;font-size:12px;padding:4px 6px;">
                <div style="font-weight:800;color:${theme.color};margin-bottom:4px;display:flex;align-items:center;gap:5px;font-family:'Outfit',sans-serif;">
                    <span style="font-family:'JetBrains Mono',monospace;">#${logIndex}</span> — ${theme.name}
                </div>
                <div style="font-size:11px;color:#cbd5e1;line-height:1.5;">
                    <div><strong>Confidence:</strong> ${confPct}</div>
                    <div><strong>Timestamp:</strong> ${timeStr} (Local)</div>
                    <div><strong>Countermeasure:</strong> ${theme.countermeasure}</div>
                    <div style="font-family:'JetBrains Mono',monospace;font-size:9.5px;color:#94a3b8;margin-top:3px;">
                        ${lat.toFixed(6)}°, ${lon.toFixed(6)}°
                    </div>
                </div>
            </div>
        `);

        mapMarkerObj = {
            marker,
            type: theme.id,
            typeName: theme.name,
            logIndex,
            lat,
            lon
        };

        // ── ENFORCE RETENTION RULES ──
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
    }

    // ── Add to Forensic Incident Ledger Table ──
    const row = document.createElement('tr');
    row.className = 'hover:bg-slate-800/40 transition-colors cursor-pointer group';
    row.innerHTML = `
        <td class="py-2.5 px-3 text-cyan-300 font-bold">#${logIndex}</td>
        <td class="py-2.5 px-3 text-brand-muted font-mono">${timeStr}</td>
        <td class="py-2.5 px-3 font-semibold" style="color: ${theme.color}">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background-color:${theme.color};margin-right:6px;box-shadow:0 0 6px ${theme.color};"></span>
            ${theme.name} <span class="text-[10px] text-brand-muted">(${confPct})</span>
        </td>
        <td class="py-2.5 px-3 text-slate-300">${theme.countermeasure}</td>
        <td class="py-2.5 px-3 font-mono text-[9px] text-cyan-400/80 truncate max-w-[90px]">${hash}</td>
    `;

    // Clicking row centers map on that attack's dot
    row.addEventListener('click', () => {
        if (mapMarkerObj) {
            map.flyTo([lat, lon], 18, { animate: true, duration: 1.0 });
            mapMarkerObj.marker.openPopup();
        }
    });

    tbody.prepend(row);

    // Keep visible ledger entries tidy (max 10 rows)
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
        hash,
        coordinates: { lat, lon }
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

// Sleek Liquid Glassmorphic Toast Notification
function showOperatorToast(message, color) {
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-6 right-6 z-50 glass-card px-4 py-3.5 rounded-xl flex items-center gap-3 border shadow-2xl transition-all duration-300 max-w-md';
    toast.style.borderColor = color || '#00f0ff';
    toast.style.boxShadow = `0 10px 30px rgba(0,0,0,0.7), 0 0 20px ${color || '#00f0ff'}30`;
    toast.innerHTML = `
        <span class="material-symbols-outlined text-[20px]" style="color:${color || '#00f0ff'}">verified</span>
        <span class="text-xs font-mono text-white leading-snug">${message}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(12px)';
        setTimeout(() => toast.remove(), 400);
    }, 4500);
}
