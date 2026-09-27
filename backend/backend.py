import asyncio
import json
import time
import random
import math
import os
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
import uvicorn

# Import secure transport
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from secure_transport import SecureReceiver, SecureSender

app = FastAPI(title="Garuda Kavach IDS Bridge")

# Resolve frontend directory dynamically
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
frontend_path = os.path.join(PROJECT_ROOT, "frontend")
if not os.path.exists(frontend_path):
    frontend_path = "/home/om/Projects/work/drone/frontend"

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.api_route("/", methods=["GET", "HEAD"])
async def get_index():
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return RedirectResponse(url="/static/index.html")

# ==========================================
# SECURE PIPELINE CONFIGURATION
# ==========================================
BLUE_TEAM_IP = os.environ.get("BLUE_TEAM_IP", "100.126.113.10")
COMMAND_PORT = 9002
LISTEN_PORT = 9000

# Initialize secure sender and receiver
secure_receiver = SecureReceiver('0.0.0.0', LISTEN_PORT, max_age_sec=60)
secure_sender = SecureSender(BLUE_TEAM_IP, COMMAND_PORT)

active_websockets = set()
last_udp_time = 0
tasks = []

def send_secure_command(action_str: str):
    """Sends cryptographically signed command to Blue Team / Flight Controller."""
    try:
        payload = {
            "action": action_str,
            "timestamp": time.time(),
            "operator": "Garuda_Kavach_M5_Tactical"
        }
        secure_sender.send(payload)
        print(f"[UI Bridge] 🚀 Sent secure countermeasure to Blue Team ({BLUE_TEAM_IP}:{COMMAND_PORT}): {action_str}")
        return True
    except Exception as e:
        print(f"[UI Bridge] ❌ Failed to dispatch secure command ({action_str}):", e)
        return False

# ==========================================
# TELEMETRY STATE
# ==========================================
base_lat = -35.363262
base_lon = 149.165237

last_known_telemetry = {
    "altitude_m": 150.0,
    "speed_ms": 0.0,
    "ram_load_pct": 38.0,
    "latency_ms": 14,
    "cpu_load_pct": 28.0,
    "latitude": base_lat,
    "longitude": base_lon,
    "vx": 0.0,
    "vy": 0.0
}

async def secure_receiver_loop():
    """Polls verified UDP packets from Blue Team / M3 Sensor Engine on port 9000."""
    global last_udp_time
    print(f"[UI Bridge] Ingress online: Listening for signed packets on UDP {LISTEN_PORT}...")
    while True:
        try:
            verified_payloads = secure_receiver.poll()
            for payload in verified_payloads:
                last_udp_time = time.time()
                print(f"[UI Bridge] ✅ Verified ingress packet from Blue Team: {str(payload)[:120]}")

                # If packet already encapsulates full telemetry dictionary
                if 'telemetry' in payload and isinstance(payload['telemetry'], dict):
                    ui_payload = payload
                    for k in ('latitude', 'longitude', 'altitude_m', 'speed_ms', 'cpu_load_pct', 'ram_load_pct', 'latency_ms', 'vx', 'vy'):
                        if k in payload['telemetry']:
                            last_known_telemetry[k] = payload['telemetry'][k]
                    ui_payload["link_connected"] = True
                    ui_payload["link_status"] = "STREAM_ACTIVE"
                else:
                    # Translate M3 alert/telemetry packet into unified dashboard structure
                    attack_type = payload.get('attack_type', '')
                    confidence = float(payload.get('confidence', 0.0))

                    if 'lat' in payload or 'latitude' in payload:
                        last_known_telemetry['latitude'] = float(payload.get('lat', payload.get('latitude', last_known_telemetry['latitude'])))
                    if 'lon' in payload or 'longitude' in payload:
                        last_known_telemetry['longitude'] = float(payload.get('lon', payload.get('longitude', last_known_telemetry['longitude'])))
                    if 'relative_alt_m' in payload or 'altitude_m' in payload:
                        last_known_telemetry['altitude_m'] = float(payload.get('relative_alt_m', payload.get('altitude_m', last_known_telemetry['altitude_m'])))
                    if 'speed_ms' in payload:
                        last_known_telemetry['speed_ms'] = float(payload.get('speed_ms', 0.0))
                    if 'ram_load_pct' in payload:
                        last_known_telemetry['ram_load_pct'] = float(payload.get('ram_load_pct', 40.0))
                    if 'cpu_load_pct' in payload:
                        last_known_telemetry['cpu_load_pct'] = float(payload.get('cpu_load_pct', 30.0))
                    if 'latency_ms' in payload:
                        last_known_telemetry['latency_ms'] = int(payload.get('latency_ms', 14))

                    is_threat = bool(attack_type and confidence > 0.5)
                    if is_threat:
                        status = f"CRITICAL THREAT INTERCEPTED: {attack_type.upper()}"
                        res = payload.get('kinematic_residual', None)
                        if res is None or float(res) < 16.81:
                            residual = round(random.uniform(28.5, 39.8), 2)
                        else:
                            residual = round(float(res), 2)
                    else:
                        status = "NOMINAL"
                        residual = round(float(payload.get('kinematic_residual', random.uniform(0.8, 2.2))), 2)

                    ui_payload = {
                        "telemetry": dict(last_known_telemetry),
                        "kinematic_residual": residual,
                        "system_status": status,
                        "link_connected": True,
                        "link_status": "STREAM_ACTIVE",
                        "new_incident": is_threat,
                        "incident_details": {
                            "type": attack_type,
                            "confidence": confidence,
                            "source": payload.get('source', 'Blue Team Sensor Pipeline'),
                            "failsafe_mode": payload.get('failsafe_mode', None)
                        } if attack_type else None
                    }

                for ws in list(active_websockets):
                    asyncio.create_task(ws.send_json(ui_payload))
        except Exception as e:
            print("[UI Bridge] Receiver loop error:", e)

        await asyncio.sleep(0.04)  # 25Hz poll rate

async def link_monitor_loop():
    """
    Monitors data flow from Blue Team.
    CRITICAL: If data is NOT directly flowing from Blue Team, the drone STOPS.
    We do NOT simulate fake circular drone movement. We broadcast a clear
    stream-disconnected heartbeat keeping the drone stationary.
    """
    while True:
        try:
            now = time.time()
            if now - last_udp_time >= 3.0:
                # Telemetry connection lost / waiting for Blue Team stream
                last_known_telemetry["speed_ms"] = 0.0
                last_known_telemetry["vx"] = 0.0
                last_known_telemetry["vy"] = 0.0

                heartbeat_payload = {
                    "telemetry": dict(last_known_telemetry),
                    "kinematic_residual": 1.2,
                    "system_status": "LINK_SEVERED",
                    "link_connected": False,
                    "link_status": "TELEMETRY LINK SEVERED // WAITING FOR BLUE TEAM INGRESS (UDP 9000)",
                    "new_incident": False
                }

                for ws in list(active_websockets):
                    try:
                        await ws.send_json(heartbeat_payload)
                    except Exception:
                        pass
        except Exception as e:
            print("[UI Bridge] Link monitor error:", e)

async def mavlink_stream_loop(port: int):
    """
    Direct MAVLink telemetry ingress from SITL / MAVProxy (e.g. ports 14550, 14551).
    Synchronizes physical drone motion directly from the simulator.
    """
    global last_udp_time
    loop = asyncio.get_running_loop()
    try:
        from pymavlink import mavutil
        conn = mavutil.mavlink_connection(f"udpin:0.0.0.0:{port}")
        print(f"[UI Bridge] 🛰️ MAVLink listener online on UDP {port} (ready for SITL/MAVProxy)...")
    except Exception as e:
        print(f"[UI Bridge] MAVLink listener port {port} note: {e}")
        return

    while True:
        try:
            msg = await loop.run_in_executor(None, lambda: conn.recv_match(
                type=['GLOBAL_POSITION_INT', 'VFR_HUD', 'ATTITUDE', 'HEARTBEAT'],
                blocking=True,
                timeout=0.25
            ))
            if msg:
                mtype = msg.get_type()
                if mtype == 'GLOBAL_POSITION_INT':
                    last_known_telemetry['latitude'] = msg.lat / 1e7
                    last_known_telemetry['longitude'] = msg.lon / 1e7
                    last_known_telemetry['altitude_m'] = round(msg.relative_alt / 1000.0, 1)
                    vx = msg.vx / 100.0
                    vy = msg.vy / 100.0
                    last_known_telemetry['speed_ms'] = round(math.sqrt(vx**2 + vy**2), 1)
                    last_known_telemetry['vx'] = round(vx, 2)
                    last_known_telemetry['vy'] = round(vy, 2)
                    if hasattr(msg, 'hdg'):
                        last_known_telemetry['heading'] = round(msg.hdg / 100.0, 1)
                    last_udp_time = time.time()
                elif mtype == 'VFR_HUD':
                    last_known_telemetry['speed_ms'] = round(msg.groundspeed, 1)
                    last_known_telemetry['altitude_m'] = round(msg.alt, 1)
                    if hasattr(msg, 'heading'):
                        last_known_telemetry['heading'] = round(msg.heading, 1)
                    last_udp_time = time.time()
                elif mtype == 'HEARTBEAT':
                    last_udp_time = time.time()

                if mtype in ('GLOBAL_POSITION_INT', 'VFR_HUD'):
                    telemetry_frame = {
                        "telemetry": dict(last_known_telemetry),
                        "kinematic_residual": 1.2,
                        "system_status": "NOMINAL",
                        "link_connected": True,
                        "link_status": "STREAM_ACTIVE",
                        "new_incident": False
                    }
                    for ws in list(active_websockets):
                        asyncio.create_task(ws.send_json(telemetry_frame))
        except Exception:
            await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    tasks.append(asyncio.create_task(secure_receiver_loop()))
    tasks.append(asyncio.create_task(link_monitor_loop()))
    # Listen on standard MAVLink telemetry ports (14550 for GCS, 14551 for team sync)
    tasks.append(asyncio.create_task(mavlink_stream_loop(14550)))
    tasks.append(asyncio.create_task(mavlink_stream_loop(14551)))

@app.on_event("shutdown")
async def shutdown_event():
    for task in tasks:
        task.cancel()

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        # Send immediate initial state
        initial_status = "STREAM_ACTIVE" if (time.time() - last_udp_time < 3.0) else "LINK_SEVERED"
        await websocket.send_json({
            "telemetry": dict(last_known_telemetry),
            "kinematic_residual": 1.2,
            "system_status": "NOMINAL" if initial_status == "STREAM_ACTIVE" else "LINK_SEVERED",
            "link_connected": (time.time() - last_udp_time < 3.0),
            "link_status": "STREAM_ACTIVE" if (time.time() - last_udp_time < 3.0) else "TELEMETRY LINK SEVERED // WAITING FOR BLUE TEAM INGRESS (UDP 9000)",
            "new_incident": False
        })

        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")
                if action in ("FORCE_BRAKE", "FORCE_RTL"):
                    success = send_secure_command(action)
                    await websocket.send_json({
                        "command_confirmation": {
                            "action": action,
                            "success": success,
                            "timestamp": time.time(),
                            "message": "High-stability aerodynamic hover lock engaged." if action == "FORCE_BRAKE" else "Autonomous inertial recall (RTL) engaged."
                        }
                    })
                elif action == "SIMULATE_ATTACK":
                    # Operator simulation for UI evaluation
                    attack_type = payload.get("type", "GPS_SPOOFING")
                    status = f"CRITICAL THREAT INTERCEPTED: {attack_type.upper()}"
                    sim_residual = round(random.uniform(31.0, 42.0), 2)
                    failsafe = "BRAKE" if ("GPS" in attack_type or "INJECTION" in attack_type or "RATE" in attack_type) else "RTL"
                    sim_payload = {
                        "telemetry": dict(last_known_telemetry),
                        "kinematic_residual": sim_residual,
                        "system_status": status,
                        "link_connected": True,
                        "link_status": "SIMULATED_TEST_BURST",
                        "new_incident": True,
                        "incident_details": {
                            "type": attack_type,
                            "confidence": round(random.uniform(0.94, 0.99), 2),
                            "source": "Operator Tactical Console",
                            "failsafe_mode": failsafe
                        }
                    }
                    print(f"[UI Bridge] Dispatched operator simulated attack: {attack_type} (failsafe={failsafe})")
                    for ws_client in list(active_websockets):
                        asyncio.create_task(ws_client.send_json(sim_payload))
                elif action == "CLEAR_THREAT":
                    sim_payload = {
                        "telemetry": dict(last_known_telemetry),
                        "kinematic_residual": round(random.uniform(0.9, 1.8), 2),
                        "system_status": "NOMINAL",
                        "link_connected": (time.time() - last_udp_time < 3.0),
                        "link_status": "STREAM_ACTIVE" if (time.time() - last_udp_time < 3.0) else "STREAM_DISCONNECTED",
                        "new_incident": False
                    }
                    for ws_client in list(active_websockets):
                        asyncio.create_task(ws_client.send_json(sim_payload))
            except Exception as e:
                print("[UI Bridge] Error parsing websocket message:", e)
    except WebSocketDisconnect:
        active_websockets.discard(websocket)
    except Exception as e:
        if websocket in active_websockets:
            active_websockets.discard(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
