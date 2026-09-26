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
            <div class="drone-pulse" style="background: var(--hud-threat, #38BDF8); opacity: 0.4;"></div>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="position: relative; z-index: 10; color: var(--hud-threat, #38BDF8); filter: drop-shadow(0 0 5px var(--hud-threat, #38BDF8));"><circle cx="5" cy="5" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><line x1="6.4" y1="6.4" x2="17.6" y2="17.6"/><line x1="6.4" y1="17.6" x2="17.6" y2="6.4"/><circle cx="12" cy="12" r="3"/></svg>
           </div>`,
    iconSize: [40, 40],
    iconAnchor: [20, 20]
});

let droneMarker = L.marker([-35.363262, 149.165237], { icon: droneIcon }).addTo(map);
let flightPath = L.polyline([], { color: '#38BDF8', weight: 3, opacity: 0.8, dashArray: '6, 6' }).addTo(map);


// ==========================================
// 2. KINEMATIC CHART INITIALIZATION
// ==========================================
const ctx = document.getElementById('residualChart').getContext('2d');
const maxDataPoints = 50; 

let gradientFill = ctx.createLinearGradient(0, 0, 0, 160);
gradientFill.addColorStop(0, 'rgba(56, 189, 248, 0.3)');
gradientFill.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

const residualChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: Array(maxDataPoints).fill(''),
        datasets: [
            {
                label: ' PHYSICS VS GPS DEVIATION',
                data: Array(maxDataPoints).fill(0),
                borderColor: '#38BDF8',
                backgroundColor: gradientFill,
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.3
            },
            {
                label: ' THRESHOLD (16.81 χ²)',
                data: Array(maxDataPoints).fill(16.81),
                borderColor: '#F59E0B',
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
    const altTrendColor = currentAlt > prevAlt ? '#10B981' : (currentAlt < prevAlt ? '#EF4444' : '#F8FAFC');
    const spdTrend = currentSpd > prevSpd ? '▲' : (currentSpd < prevSpd ? '▼' : '');
    const spdTrendColor = currentSpd > prevSpd ? '#10B981' : (currentSpd < prevSpd ? '#EF4444' : '#F8FAFC');
    
    prevAlt = currentAlt;
    prevSpd = currentSpd;

    // Update Telemetry Panel
    const altEl = document.getElementById("alt-val");
    if(altEl) altEl.innerHTML = `<span style="color:${altTrendColor}; font-size:14px;">${altTrend}</span> ${currentAlt.toFixed(1)}m`;
    const spdEl = document.getElementById("spd-val");
    if(spdEl) spdEl.innerHTML = `<span style="color:${spdTrendColor}; font-size:14px;">${spdTrend}</span> ${currentSpd.toFixed(1)}m/s`;
    
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
    if(cpuGauge && cpuText) {
        cpuGauge.setAttribute("stroke-dasharray", `${cpuPct}, 100`);
        cpuText.textContent = `${cpuPct.toFixed(1)}%`;
        if (cpuPct > 85) cpuGauge.style.stroke = '#EF4444';
        else if (cpuPct > 60) cpuGauge.style.stroke = '#F59E0B';
        else cpuGauge.style.stroke = '#38BDF8';
    }

    // RAM Gauge Update
    const ramPct = telemetry.ram_load_pct !== undefined ? telemetry.ram_load_pct : 0;
    const ramGauge = document.getElementById("ram-gauge");
    const ramText = document.getElementById("ram-val-text");
    if(ramGauge && ramText) {
        ramGauge.setAttribute("stroke-dasharray", `${ramPct}, 100`);
        ramText.textContent = `${ramPct.toFixed(1)}%`;
        if (ramPct > 85) ramGauge.style.stroke = '#EF4444';
        else if (ramPct > 60) ramGauge.style.stroke = '#F59E0B';
        else ramGauge.style.stroke = '#38BDF8';
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
    [tGps, tDos, tCmd, tRpl].forEach(el => {
        if (el) el.className = "threat-item";
    });
    
    const system_status = data.system_status || "NOMINAL";

    if (system_status !== "NOMINAL") {
        document.getElementById("status-banner").className = "header threat";
        document.getElementById("status-icon").className = "fa-solid fa-radiation";
        document.getElementById("status-text").innerText = "[ CRITICAL THREAT INTERCEPTED: " + system_status.replace('CRITICAL THREAT INTERCEPTED: ', '') + " ]";
        
        if (window.currentThreatState !== system_status) {
            document.body.classList.add("critical-threat-mode");
            if (window.threatFlashTimeout) clearTimeout(window.threatFlashTimeout);
            window.threatFlashTimeout = setTimeout(() => {
                document.body.classList.remove("critical-threat-mode");
            }, 1300);
            window.currentThreatState = system_status;
        }
        
        if (system_status.includes("GPS")) {
            tGps.classList.add("active-gps");
            flightPath.setStyle({ color: '#EF4444' }); // Red for GPS Spoof
            document.documentElement.style.setProperty('--hud-threat', '#EF4444');
        } else if (system_status.includes("FLOOD")) {
            tDos.classList.add("active-dos");
            flightPath.setStyle({ color: '#F59E0B' }); // Amber for DoS
            document.documentElement.style.setProperty('--hud-threat', '#F59E0B');
        } else if (system_status.includes("INJECTION") || system_status.includes("ROGUE")) {
            tCmd.classList.add("active-cmd");
            flightPath.setStyle({ color: '#A855F7' }); // Purple for Injection
            document.documentElement.style.setProperty('--hud-threat', '#A855F7');
        } else if (system_status.includes("ANOMALY")) {
            tRpl.classList.add("active-cmd"); // Reuse active-cmd style for purple
            flightPath.setStyle({ color: '#A855F7' }); // Purple
            document.documentElement.style.setProperty('--hud-threat', '#A855F7');
        } else {
            flightPath.setStyle({ color: '#EF4444' });
            document.documentElement.style.setProperty('--hud-threat', '#EF4444');
        }
        
    } else {
        window.currentThreatState = "NOMINAL";
        document.getElementById("status-banner").className = "header safe";
        document.getElementById("status-icon").className = "fa-solid fa-shield-halved";
        document.getElementById("status-text").innerText = "[ SYSTEMS NOMINAL ] SYS.TRACKING // AIRSPACE SECURE";
        
        document.body.classList.remove("critical-threat-mode");
        // Flight trail cyan
        flightPath.setStyle({ color: '#38BDF8' });
        document.documentElement.style.setProperty('--hud-threat', '#38BDF8');
    }

    // Ledger Handling
    if (data.new_incident) {
        incidentLog.push(data.new_incident);
        const logIndex = data.incident_index || incidentLog.length;
        const threatText = data.new_incident.threat;
        
        let threatColor = '#EF4444'; // default red
        if (threatText.includes("GPS")) threatColor = '#EF4444'; // Red
        else if (threatText.includes("FLOOD")) threatColor = '#F59E0B'; // Amber
        else if (threatText.includes("INJECTION") || threatText.includes("ROGUE") || threatText.includes("ANOMALY")) threatColor = '#A855F7'; // Purple
        
        const tbody = document.getElementById("ledger-body");
        const row = document.createElement("tr");
        row.innerHTML = `
            <td>#${logIndex}</td>
            <td>[${data.new_incident.timestamp}]</td>
            <td class="threat-text" style="color: ${threatColor}">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background-color:${threatColor}; margin-right:6px; box-shadow: 0 0 6px ${threatColor};"></span>
                ${threatText}
            </td>
            <td class="action-text">${data.new_incident.action}</td>
            <td class="hash-text">${data.new_incident.hash}</td>
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
    document.getElementById("status-banner").className = "header threat";
    document.getElementById("status-icon").className = "fa-solid fa-triangle-exclamation";
    document.getElementById("status-text").innerText = "SYS.FAULT // CONNECTION TO DAEMON LOST";
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
