// ==========================================
// 1. TACTICAL MAP INITIALIZATION (Leaflet)
// ==========================================
const map = L.map('tactical-map', {
    zoomControl: false,
    attributionControl: false
}).setView([-35.363262, 149.165237], 18);

// Google Satellite Hybrid
L.tileLayer('http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}', {
    maxZoom: 20,
    attribution: 'Google Maps'
}).addTo(map);

// Custom Drone SVG Icon
const droneIcon = L.divIcon({
    className: 'custom-drone-icon',
    html: `<div style="position: relative; width: 40px; height: 40px; transform: rotate(0deg);" id="drone-marker">
            <div class="drone-pulse" style="background: var(--hud-threat, #00f0ff); opacity: 0.4;"></div>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="position: relative; z-index: 10; color: var(--hud-threat, #00f0ff); filter: drop-shadow(0 0 5px var(--hud-threat, #00f0ff));"><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><line x1="6.4" y1="6.4" x2="17.6" y2="17.6"/><line x1="6.4" y1="17.6" x2="17.6" y2="6.4"/><circle cx="12" cy="12" r="3"/></svg>
           </div>`,
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

let droneMarker = L.marker([-35.363262, 149.165237], { icon: droneIcon }).addTo(map);
let flightPath = L.polyline([], { color: '#00f0ff', weight: 3, opacity: 0.8, dashArray: '6, 6' }).addTo(map);


// ==========================================
// 2. KINEMATIC CHART INITIALIZATION
// ==========================================
const ctx = document.getElementById('residualChart').getContext('2d');
const maxDataPoints = 50; 

let gradientFill = ctx.createLinearGradient(0, 0, 0, 160);
gradientFill.addColorStop(0, 'rgba(56, 189, 248, 0.6)');
gradientFill.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

const residualChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: Array(maxDataPoints).fill(''),
        datasets: [
            {
                label: ' PHYSICS VS GPS DEVIATION',
                data: Array(maxDataPoints).fill(0),
                borderColor: '#00f0ff',
                backgroundColor: gradientFill,
                borderWidth: 3,
                pointRadius: 0,
                fill: true,
                tension: 0.5
            },
            {
                label: ' THRESHOLD (16.81 χ²)',
                data: Array(maxDataPoints).fill(16.81),
                borderColor: '#f59e0b',
                borderWidth: 1.5,
                borderDash: [4, 4],
                pointRadius: 0,
                fill: false
            }
        ]
    },
    options: {
        responsive: true, maintainAspectRatio: false, animation: false,
        scales: {
            y: {
                min: 0, max: 40,
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#94A3B8', font: { family: 'JetBrains Mono', size: 11 } }
            },
            x: { display: false }
        },
        plugins: { legend: { labels: { color: '#F8FAFC', font: { family: 'Inter', size: 12, weight: '500' } } } },
        interaction: { intersect: false, mode: 'index' }
    }
});


// ==========================================
// 2.5 INTERACTIVE RADAR & BLIPS
// ==========================================
const radarElement = document.querySelector('.radar');
let radarTargets = [];

const radarParent = document.querySelector('.tactical-grid-bg') || (radarElement ? radarElement.parentElement : null);
if (radarParent && radarElement) {
    // Interactivity: Add mouse tracking for scanning focus
    radarParent.addEventListener('mousemove', (e) => {
        const rect = radarParent.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        radarElement.style.background = `radial-gradient(circle at ${x}px ${y}px, rgba(56, 189, 248, 0.3) 0%, rgba(15, 23, 42, 0.9) 100%)`;
    });
    radarParent.addEventListener('mouseleave', () => {
        radarElement.style.background = `radial-gradient(circle, rgba(56, 189, 248, 0.1) 0%, rgba(15, 23, 42, 0.8) 100%)`;
    });

    // Populate with 3 initial "ambient" blips
    for(let i=0; i<3; i++) spawnRadarBlip('#00f0ff', true);
}

function spawnRadarBlip(color, isAmbient = false) {
    if (!radarElement) return;
    const blip = document.createElement('div');
    blip.className = 'radar-blip';
    blip.style.backgroundColor = color;
    blip.style.boxShadow = `0 0 10px ${color}, 0 0 20px ${color}`;
    
    // Start somewhere away from center
    const angle = Math.random() * Math.PI * 2;
    const dist = 15 + Math.random() * 30;
    
    blip.dataset.angle = angle;
    blip.dataset.dist = dist;
    blip.dataset.speed = (Math.random() * 0.01 + 0.005) * (Math.random() > 0.5 ? 1 : -1);
    
    radarElement.appendChild(blip);
    radarTargets.push(blip);

    if (!isAmbient) {
        blip.style.width = '8px';
        blip.style.height = '8px';
        blip.style.animationDuration = '1.5s'; // pulse faster for threats
        setTimeout(() => {
            if (blip.parentNode) blip.parentNode.removeChild(blip);
            radarTargets = radarTargets.filter(b => b !== blip);
        }, 6000);
    }
}

// Update radar blips position on animation frame
function animateRadar() {
    radarTargets.forEach(blip => {
        let angle = parseFloat(blip.dataset.angle);
        let dist = parseFloat(blip.dataset.dist);
        angle += parseFloat(blip.dataset.speed);
        blip.dataset.angle = angle;
        
        const x = 50 + Math.cos(angle) * dist;
        const y = 50 + Math.sin(angle) * dist;
        blip.style.left = `${x}%`;
        blip.style.top = `${y}%`;
    });
    requestAnimationFrame(animateRadar);
}
animateRadar();


// ==========================================
// 3. WEBSOCKET CONNECTION
// ==========================================
const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
const ws = new WebSocket(`${protocol}//${window.location.host}/ws/telemetry`);

let incidentLog = []; 
let prevAlt = 0;
let prevSpd = 0;

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    const telemetry = data.telemetry || {};
    // Calculate Trends
    const currentAlt = telemetry.altitude_m !== undefined ? telemetry.altitude_m : prevAlt;
    const currentSpd = telemetry.speed_ms !== undefined ? telemetry.speed_ms : prevSpd;
    
    const altTrend = currentAlt > prevAlt ? '▲' : (currentAlt < prevAlt ? '▼' : '');
    const altTrendColor = currentAlt > prevAlt ? '#00f0ff' : (currentAlt < prevAlt ? '#ef4444' : '#F8FAFC');
    const spdTrend = currentSpd > prevSpd ? '▲' : (currentSpd < prevSpd ? '▼' : '');
    const spdTrendColor = currentSpd > prevSpd ? '#00f0ff' : (currentSpd < prevSpd ? '#ef4444' : '#F8FAFC');
    
    prevAlt = currentAlt;
    prevSpd = currentSpd;

    // Update Telemetry Panel
    const altEl = document.getElementById("alt-val");
    if(altEl) altEl.innerHTML = `<span style="color:${altTrendColor}; font-size:14px;">${altTrend}</span> ${currentAlt.toFixed(1)}m`;
    const spdEl = document.getElementById("spd-val");
    if(spdEl) spdEl.innerHTML = `<span style="color:${spdTrendColor}; font-size:14px;">${spdTrend}</span> ${currentSpd.toFixed(1)}m/s`;
    
    
    // Update Segmented Bars
    function updateSegments(id, pct) {
        const container = document.getElementById(id);
        if(container) {
            const divs = container.querySelectorAll('div');
            const activeCount = Math.floor((pct / 100) * divs.length);
            divs.forEach((div, idx) => {
                div.className = (idx < activeCount) ? 'h-full w-full bg-brand-accent rounded-sm' : 'h-full w-full bg-brand-border rounded-sm';
            });
        }
    }
    
    function updateCpuSegments(pct) {
        const container = document.getElementById('cpu-segments');
        if(container) {
            const children = Array.from(container.children);
            const activeCount = Math.floor((pct / 100) * children.length);
            children.forEach((outerDiv, idx) => {
                const innerDiv = outerDiv.firstElementChild;
                if(innerDiv) {
                    let h = 50 + (idx % 3) * 20;
                    let c = (idx < activeCount) ? 'bg-brand-danger' : 'bg-brand-accent';
                    innerDiv.className = `w-full ${c} transition-all h-[${h}%]`;
                }
            });
        }
    }
    
    const altPct = Math.min((currentAlt / 200) * 100, 100);
    updateSegments('alt-segments', altPct);
    
    const spdPct = Math.min((currentSpd / 25) * 100, 100);
    updateSegments('spd-segments', spdPct);
    
    if(telemetry.cpu_load_pct !== undefined) {
        updateCpuSegments(telemetry.cpu_load_pct);
    }
    
    const ramFill = document.getElementById('ram-fill');
    if(ramFill) {
        const ramPct = telemetry.ram_load_pct !== undefined ? telemetry.ram_load_pct : 0;
        ramFill.style.width = `${ramPct}%`;
    }

    // Altitude Gauge (Mock max 200m for percentage)
    const altGauge = document.getElementById("alt-gauge");
    if(altGauge) {
        const altPct = Math.min((currentAlt / 200) * 100, 100);
        altGauge.setAttribute("stroke-dasharray", `${altPct}, 100`);
    }
    
    // Speed Gauge (Mock max 25m/s for percentage)
    const spdGauge = document.getElementById("spd-gauge");
    if(spdGauge) {
        const spdPct = Math.min((currentSpd / 25) * 100, 100);
        spdGauge.setAttribute("stroke-dasharray", `${spdPct}, 100`);
    }

    if (telemetry.ram_load_pct !== undefined) {
        const ramEl = document.getElementById("ram-val");
        if(ramEl) ramEl.innerText = telemetry.ram_load_pct.toFixed(1);
    }
    if (telemetry.latency_ms !== undefined) {
        document.getElementById("lat-val").innerText = telemetry.latency_ms;
    }
    
    // CPU Gauge Update
    const cpuPct = telemetry.cpu_load_pct !== undefined ? telemetry.cpu_load_pct : 0;
    const cpuGauge = document.getElementById("cpu-gauge");
    const cpuText = document.getElementById("cpu-val-text");
    if(cpuText) cpuText.textContent = `${cpuPct.toFixed(1)}%`;
    if(cpuGauge) {
        cpuGauge.setAttribute("stroke-dasharray", `${cpuPct}, 100`);
        if (cpuPct > 85) cpuGauge.style.stroke = '#ef4444';
        else if (cpuPct > 60) cpuGauge.style.stroke = '#f59e0b';
        else cpuGauge.style.stroke = '#00f0ff';
    }

    // RAM Gauge Update
    const ramPct = telemetry.ram_load_pct !== undefined ? telemetry.ram_load_pct : 0;
    const ramGauge = document.getElementById("ram-gauge");
    const ramText = document.getElementById("ram-val-text");
    if(ramText) ramText.textContent = `${ramPct.toFixed(1)}%`;
    if(ramGauge) {
        ramGauge.setAttribute("stroke-dasharray", `${ramPct}, 100`);
        if (ramPct > 85) ramGauge.style.stroke = '#ef4444';
        else if (ramPct > 60) ramGauge.style.stroke = '#f59e0b';
        else ramGauge.style.stroke = '#00f0ff';
    }
    
    // Update Map
    const lat = telemetry.latitude !== undefined ? telemetry.latitude : 0;
    const lon = telemetry.longitude !== undefined ? telemetry.longitude : 0;
    document.getElementById("lat-display").innerText = lat.toFixed(6);
    document.getElementById("lon-display").innerText = lon.toFixed(6);
    
    if (lat !== 0 && lon !== 0) {
        droneMarker.setLatLng([lat, lon]);
        flightPath.addLatLng([lat, lon]);
        
        // Prevent memory bloat on long missions
        const latlngs = flightPath.getLatLngs();
        if (latlngs.length > 2000) {
            latlngs.shift();
            flightPath.setLatLngs(latlngs);
        }
        
        // Throttle pan to prevent lag
        if (!window.panTick) window.panTick = 0;
        if (window.panTick++ % 10 === 0) {
            map.panTo([lat, lon], { animate: true, duration: 1.0 });
        }
    }

    // Rotate marker based on heading (derived from vx/vy)
    const vx = telemetry.vx !== undefined ? telemetry.vx : 0;
    const vy = telemetry.vy !== undefined ? telemetry.vy : 0;
    const heading = Math.atan2(vy, vx) * (180 / Math.PI);
    const markerEl = document.getElementById("drone-marker");
    if(markerEl) markerEl.style.transform = `rotate(${heading}deg)`;

    // Update Chart
    const kinematic_residual = data.kinematic_residual !== undefined ? data.kinematic_residual : 0;
    residualChart.data.datasets[0].data.push(kinematic_residual);
    residualChart.data.datasets[0].data.shift();
    residualChart.update();

    // Handle Threat Matrix
    const tGps = document.getElementById("threat-gps");
    const tDos = document.getElementById("threat-dos");
    const tCmd = document.getElementById("threat-cmd");
    const tRpl = document.getElementById("threat-rpl");

    // Reset all
    const defaultThreatClass = "bg-brand-bg p-3 border-l-2 border-brand-border rounded-r transition-all duration-300";
    if (tGps) tGps.className = defaultThreatClass;
    if (tDos) tDos.className = defaultThreatClass;
    if (tCmd) tCmd.className = defaultThreatClass;
    if (tRpl) tRpl.className = defaultThreatClass;
    
    const system_status = data.system_status || "NOMINAL";

    
    if (system_status !== "NOMINAL") {
        document.getElementById("status-banner").className = "flex-none bg-brand-surface/60 backdrop-blur-lg border-b border-brand-danger shadow-[0_0_20px_rgba(239,68,68,0.4)] px-6 py-4 flex items-center justify-between transition-all duration-300";
        document.getElementById("status-icon").className = "w-3 h-3 bg-brand-danger rounded-full animate-ping";
        document.getElementById("status-text").innerText = "[ CRITICAL THREAT INTERCEPTED: " + system_status.replace('CRITICAL THREAT INTERCEPTED: ', '') + " ]";
        document.getElementById("status-text").className = "text-brand-danger";

        if (window.currentThreatState !== system_status) {
            document.body.classList.add("critical-threat-mode");
            if (window.threatFlashTimeout) clearTimeout(window.threatFlashTimeout);
            window.threatFlashTimeout = setTimeout(() => {
                document.body.classList.remove("critical-threat-mode");
            }, 1300);
            window.currentThreatState = system_status;
        }
        
        if (system_status.includes("GPS")) {
            if(tGps) {
                tGps.classList.add("shadow-[0_0_15px_rgba(239,68,68,0.5)]");
                tGps.classList.replace("bg-brand-bg", "bg-brand-danger/20"); tGps.classList.replace("border-brand-border", "border-brand-danger");
            }
            flightPath.setStyle({ color: '#ef4444' }); // Red for GPS Spoof
            document.documentElement.style.setProperty('--hud-threat', '#ef4444');
        } else if (system_status.includes("FLOOD")) {
            if(tDos) {
                tDos.classList.add("shadow-[0_0_15px_rgba(245,158,11,0.5)]");
                tDos.classList.replace("bg-brand-bg", "bg-brand-warning/20"); tDos.classList.replace("border-brand-border", "border-brand-warning");
            }
            const mavEl = document.getElementById("mavlink-status");
            if (mavEl) { mavEl.textContent = "⚠ FLOOD"; mavEl.className = "text-brand-warning animate-pulse"; }
            flightPath.setStyle({ color: '#f59e0b' }); // Amber for DoS
            document.documentElement.style.setProperty('--hud-threat', '#f59e0b');

        } else if (system_status.includes("INJECTION") || system_status.includes("ROGUE")) {
            if(tCmd) {
                tCmd.classList.add("shadow-[0_0_15px_rgba(0,240,255,0.5)]");
                tCmd.classList.replace("bg-brand-bg", "bg-brand-danger/20"); tCmd.classList.replace("border-brand-border", "border-brand-danger");
            }
            flightPath.setStyle({ color: '#ef4444' }); // Purple for Injection
            document.documentElement.style.setProperty('--hud-threat', '#ef4444');
        } else if (system_status.includes("ANOMALY")) {
            if(tRpl) {
                tRpl.classList.add("shadow-[0_0_15px_rgba(0,240,255,0.5)]");
                tRpl.classList.replace("bg-brand-bg", "bg-brand-danger/20"); tRpl.classList.replace("border-brand-border", "border-brand-danger");
            }
            flightPath.setStyle({ color: '#ef4444' }); // Purple
            document.documentElement.style.setProperty('--hud-threat', '#ef4444');
        } else {
            flightPath.setStyle({ color: '#ef4444' });
            document.documentElement.style.setProperty('--hud-threat', '#ef4444');
        }
        
    
    } else {
        window.currentThreatState = "NOMINAL";
        document.getElementById("status-banner").className = "flex-none bg-brand-surface/60 backdrop-blur-lg border-b border-brand-accent/50 shadow-[0_0_20px_rgba(0,229,255,0.2)] px-6 py-4 flex items-center justify-between transition-all duration-300";
        document.getElementById("status-icon").className = "w-3 h-3 bg-brand-accent rounded-full animate-pulse";
        document.getElementById("status-text").innerText = "GARUDAKAAVACH // IDS SENSOR FUSION";
        document.getElementById("status-text").className = "";
        const mavEl = document.getElementById("mavlink-status");
        if (mavEl) { mavEl.textContent = "NOMINAL"; mavEl.className = "text-brand-accent"; }

        document.body.classList.remove("critical-threat-mode");
        // Flight trail cyan
        flightPath.setStyle({ color: '#00f0ff' });
        document.documentElement.style.setProperty('--hud-threat', '#00f0ff');
    }

    // Ledger Handling
    if (data.new_incident) {
        incidentLog.push(data.new_incident);
        const logIndex = data.incident_index || incidentLog.length;
        const threatText = data.new_incident.threat;
        
        let threatColor = '#ef4444'; // default red
        if (threatText.includes("GPS")) threatColor = '#ef4444'; // Red
        else if (threatText.includes("FLOOD")) threatColor = '#f59e0b'; // Amber
        else if (threatText.includes("INJECTION") || threatText.includes("ROGUE") || threatText.includes("ANOMALY")) threatColor = '#ef4444'; // Purple
        
        if (typeof spawnRadarBlip === 'function') {
            spawnRadarBlip(threatColor, false);
        }

        const tbody = document.getElementById("ledger-body");
        const row = document.createElement("tr");
        row.className = 'hover:bg-surface-container-high/50 transition-colors';
        row.innerHTML = `
            <td class="py-2 px-3 text-on-surface-variant font-mono">#${logIndex}</td>
            <td class="py-2 px-3 text-tertiary-container font-mono">[${data.new_incident.timestamp}]</td>
            <td class="py-2 px-3 font-bold" style="color: ${threatColor}">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background-color:${threatColor}; margin-right:6px; box-shadow: 0 0 6px ${threatColor};"></span>
                ${threatText}
            </td>
            <td class="py-2 px-3 text-on-surface-variant">${data.new_incident.action}</td>
            <td class="py-2 px-3 text-on-surface-variant font-mono text-[9px] truncate max-w-[100px]">${data.new_incident.hash}</td>
        `;
        tbody.prepend(row);
        
        // Limit to last 3 attacks in the UI list
        while (tbody.children.length > 3) {
            tbody.removeChild(tbody.lastChild);
        }
        
        // Add Map Marker
        const attackMarkerIcon = L.divIcon({
            className: 'attack-marker-icon',
            html: `<div style="width: 14px; height: 14px; border-radius: 50%; background-color: ${threatColor}; border: 2px solid white; box-shadow: 0 0 8px ${threatColor};"></div>`,
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });
        
        const attackMarker = L.marker([lat, lon], { icon: attackMarkerIcon }).addTo(map);
        attackMarker.bindPopup(`<div style="font-family:'Inter',sans-serif;font-size:12px;">This attack happened on <b>${data.new_incident.timestamp}</b> and its report is saved in <b>#${logIndex}</b></div>`);
        
        if (!window.attackMarkers) window.attackMarkers = [];
        window.attackMarkers.push({ marker: attackMarker, type: threatText });
        
        // Limit to last 5 of the same type
        const typeMarkers = window.attackMarkers.filter(m => m.type === threatText);
        if (typeMarkers.length > 5) {
            const oldestOfType = typeMarkers[0];
            map.removeLayer(oldestOfType.marker);
            window.attackMarkers = window.attackMarkers.filter(m => m !== oldestOfType);
        }
        
        // Limit to last 15 attack markers total
        if (window.attackMarkers.length > 15) {
            const oldest = window.attackMarkers.shift();
            map.removeLayer(oldest.marker);
        }
    }
};

ws.onclose = function() {
    document.getElementById("status-banner").className = "flex-none bg-brand-surface/60 backdrop-blur-lg border-b border-brand-danger shadow-[0_0_20px_rgba(239,68,68,0.4)] px-6 py-4 flex items-center justify-between transition-all duration-300";
    document.getElementById("status-icon").className = "w-3 h-3 bg-brand-danger rounded-full animate-ping";
    document.getElementById("status-text").innerText = "SYS.FAULT // CONNECTION TO DAEMON LOST";
    document.getElementById("status-text").className = "text-brand-danger";
};

// ==========================================
// 4. MANUAL CONTROLS & EXPORTS
// ==========================================
document.getElementById("export-btn").addEventListener("click", function() {
    if (incidentLog.length === 0) return alert("No incidents recorded in the ledger.");
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(incidentLog, null, 2));
    const dl = document.createElement('a'); dl.setAttribute("href", dataStr); dl.setAttribute("download", "pushpak_forensics.json");
    document.body.appendChild(dl); dl.click(); dl.remove();
});

document.querySelector('.btn-brake').addEventListener("click", () => {
    if(ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({action: "FORCE_BRAKE"}));
        alert("MANUAL OVERRIDE: BRAKE command sent to Daemon.");
    }
});

document.querySelector('.btn-rtl').addEventListener("click", () => {
    if(ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({action: "FORCE_RTL"}));
        alert("MANUAL OVERRIDE: RTL command sent to Daemon.");
    }
});


// ==========================================
// 5. ANIMATE RF SPECTRUM
// ==========================================
function animateSpectrum() {
    const barsContainer = document.getElementById('rf-spectrum-bars');
    if (barsContainer) {
        const bars = barsContainer.querySelectorAll('div');
        bars.forEach((bar, index) => {
            const isThreat = window.currentThreatState && window.currentThreatState !== "NOMINAL";
            const minHeight = (index === 5 && isThreat) ? 80 : 10;
            const maxHeight = (index === 5 && isThreat) ? 100 : (index === 5 ? 60 : 70);
            const randomHeight = Math.floor(Math.random() * (maxHeight - minHeight + 1)) + minHeight;
            bar.style.height = `${randomHeight}%`;
            bar.style.transition = 'height 0.3s ease';
        });
    }
}
setInterval(animateSpectrum, 300);
