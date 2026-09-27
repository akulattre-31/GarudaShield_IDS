# 🛡️ Garuda Kavach — M5 Tactical Defense Dashboard
**Cyber-Physical Drone Intrusion Detection System (IDS) Frontend & UI Bridge**  
*Team Garuda Kavach*

---

## 🛰️ 1. Overview & Architecture

The **Garuda Kavach M5 Tactical Dashboard** is an aerospace-grade, cyber-physical air defense console designed to provide real-time situational awareness, multi-vector threat detection, and instant countermeasure execution for autonomous aerial systems.

Built with a **Liquid Glassmorphism** design system and defense cyber typography, the dashboard serves as the human-in-the-loop tactical interface for drone operators, mission commanders, and blue team analysts.

```
┌─────────────────────────────────┐
│     Blue Team Sensor Pipeline   │
│   (M3 Detection & EKF Engine)   │
└───────────────┬─────────────────┘
                │  UDP 9000 (Signed HMAC-SHA256 Envelopes)
                ▼
┌─────────────────────────────────┐
│   M5 Backend Bridge (FastAPI)   │
│     backend/backend.py          │
└───────────────┬─────────────────┘
                │  WebSocket 20Hz (/ws/telemetry)
                ▼
┌─────────────────────────────────┐       UDP 9002 (Signed HMAC Commands)
│   Garuda Kavach Frontend UI     │ ────────────────────────────────────────► Blue Team / Drone Autopilot
│  (app.js, index.html, style.css)│  (Airborne Brake / Autonomous RTL)        (Zero-Velocity Hover / RTL)
└─────────────────────────────────┘
```

---

## ⚡ 2. How the Frontend Connects to the Blue Team

### A. Inbound Telemetry & Threat Ingress (Port 9000)
1. **Blue Team Sensor Pipeline / M3 Engine**: Continuously processes MAVLink flight packets, Kalman filters, eBPF packet inspection, and cryptographic signatures.
2. **Cryptographic Sealing**: Blue Team signs JSON payloads using **HMAC-SHA256** with shared secret key `keys/pipeline.key`.
3. **M5 Python Bridge (`backend/backend.py`)**:
   - Listens on `0.0.0.0:9000` via non-blocking `SecureReceiver`.
   - Rejects unsigned, forged, or stale packets (>60s old).
   - Translates verified packets into structured UI telemetry frames.
   - Pushes frames over a persistent low-latency WebSocket connection (`ws://<host>:8000/ws/telemetry`) to all connected browser clients at 20–25Hz.

### B. Outbound Tactical Countermeasures (Port 9002)
1. **Operator Command Trigger**: When the operator clicks an Emergency Countermeasure (e.g., *Immediate Airborne Brake* or *Autonomous Return to Base*), `app.js` dispatches an action payload across the WebSocket to `backend/backend.py`.
2. **HMAC Signing**: The backend seals the action with `keys/pipeline.key` and transmits an authenticated UDP packet to the Blue Team / Flight Controller at `100.126.113.10:9002`.
3. **Execution & Feedback**: The flight controller executes the autopilot mode switch (Position Hold or RTL) and the dashboard receives immediate visual confirmation.

### C. Link Failure & Stream Inactive Protection (No Fake Circular Drift)
- If the incoming stream on UDP 9000 stops or drops for > 3.0 seconds, the frontend **immediately halts the drone** in its last known position.
- Fake circular coordinate movement is strictly forbidden.
- The UI status updates to `TELEMETRY LINK SEVERED // WAITING FOR BLUE TEAM INGRESS (UDP 9000)`.
- Speed is set to `0.0 m/s` and the beside-drone 3D cube displays `DRONE-01 // STATIONARY`.

---

## 🖥️ 3. Frontend Components & Interface Guide

### 1. Centered Header & Human Local Clock
- **Centered Title**: "GARUDA KAVACH" with cyber defense shield and team banner (*Team Garuda Kavach*).
- **Left Indicator**: Pulse beacon displaying live ingress feed state (`Sentinel Shield Online` or `Telemetry Link Severed`).
- **Right Clock**: Real-time Human Local Clock (`HH:MM:SS` with local timezone, e.g. `IST`), completely devoid of robotic "Zulu" phrasing.

### 2. Tactical Leaflet Satellite Map & Coordinates
- **Satellite Hybrid Basemap**: Google Satellite Hybrid imagery centered on drone sector coordinates.
- **Full Page Scrollability**: Map `scrollWheelZoom` is disabled so mouse wheel scrolls the page smoothly.
- **Corner Map Coordinates HUD**: A liquid glassmorphic card anchored at the bottom-left corner of the map displaying high-precision nav coordinates:
  - Latitude: `-35.363262°`
  - Longitude: `149.165237°`
  - Altitude: `150.0m`
  - RTK-3D GPS Lock status
- **Beside-Drone 3D Holographic Cube HUD**: A miniature glass cube tracking right beside the drone marker on the map displaying live latitude, longitude, altitude, and current flight status. Turns alert crimson when under attack.

### 3. Real-Time Moving Anomaly Waveform Graph
- **Dynamic Oscilloscope**: Continuously scrolling waveform monitoring Kinematic Residual ($\chi^2$).
- **Threshold Line**: Dashed golden threshold marker at **16.81 $\chi^2$**.
- **Sudden Spike Detection**: When an attack or sensor divergence occurs, the waveform spikes sharply to $30–45\ \chi^2$, turns glowing threat crimson, flashes the container card, logs the forensic incident, and drops a colored attack marker on the map.

### 4. Threat Watch Matrix & Attack Color Coding
Every attack type is assigned a distinct tactical neon color:
| Attack Type | Signature Key | Color Code | Countermeasure Action |
|:---|:---|:---|:---|
| **GPS Spoofing** | `GPS_SPOOFING` | **Neon Crimson** (`#ff2a55`) | Inertial Position Lock & Optical Hover |
| **MAVLink Rate Flood** | `MAVLINK_FLOOD` | **Vivid Amber** (`#ff9900`) | Kernel eBPF Packet Ingress Throttling |
| **Command Injection** | `COMMAND_INJECTION` | **Electric Violet** (`#a855f7`) | Cryptographic Ed25519 Auth Drop |
| **Replay Attack** | `REPLAY_ATTACK` | **Neon Cyan** (`#00e5ff`) | Temporal Freshness Nonce Expiry |
| **Sensor Anomaly** | `SENSOR_ANOMALY` | **Neon Emerald** (`#10b981`) | EKF Chi-Square Decoupling Failsafe |

- **Map Dot Retention Rules**:
  1. *Same Attack Type*: At most the past **5** recorded dots are retained on the map. Older dots of that specific type are automatically pruned.
  2. *Across All Attacks*: At most **10 total** dots are retained on the map simultaneously.
- **Interactive Test Buttons**: Each threat card contains a "Test Spike" trigger allowing operators to simulate intrusion events and verify the defense pipeline instantly.

### 5. Forensic Incident Ledger
- Tabulates all detected incidents with:
  - Incident number (`#01`, `#02`...)
  - Human Local Timestamp
  - Attack Signature (with colored status dot and confidence score)
  - Dispatched Countermeasure
  - Cryptographic Verification Token / Hash
- **Map Focus**: Clicking any row smoothly flies the satellite map camera to that attack's marker location and displays full incident metadata.
- **JSON Export**: Allows operators to download forensic logs for compliance and incident post-mortems.

### 6. Emergency Countermeasures (Human-Explainable Rationale)
Replaces robotic actuator controls with clear, mission-critical failsafes:
1. **Immediate Airborne Brake**:
   - *Why needed:* Zeroes translational velocity vectors and forces the drone into an aerodynamic stationary hover, preventing unauthorized flight deviation or hijacking into restricted airspace.
2. **Autonomous Return to Base (RTL)**:
   - *Why needed:* Swaps autopilot to autonomous inertial dead-reckoning recall, ignoring compromised external telemetry and spoofed GPS to safely guide the drone home.

---

## 🚀 4. How to Run the Frontend & UI Bridge

### Prerequisites
- Python 3.10+ (with virtual environment in `drvenv`)
- Packages: `fastapi`, `uvicorn`, `pymavlink`, `websockets`
- Shared HMAC key at `keys/pipeline.key`

### Launch Command
```bash
cd /home/om/GarudaShield_IDS
/home/om/Projects/work/drone/drvenv/bin/python backend/backend.py
```

### Accessing the Dashboard
- **Web Browser**: Open `http://localhost:8000/` or `http://<your-tailscale-ip>:8000/`
- The browser will automatically load the Liquid Glassmorphic Dashboard.
