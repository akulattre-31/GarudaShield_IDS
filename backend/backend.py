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
import sys
import threading
from pymavlink import mavutil

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

SITL_IP = os.environ.get("SITL_IP", "100.113.116.76")

def send_mavlink_direct_command(action_str: str) -> bool:
    """
    Sends MAVLink mode-change directly to ArduPilot SITL (Akul's simulator).
    Used as primary path for Brake/RTL — does not depend on Blue Team being online.
    Tries multiple SITL ports sequentially until one responds with a heartbeat.
    """
    SITL_PORTS = ["tcp:100.113.116.76:5762", "tcp:100.113.116.76:5763", "udpout:100.113.116.76:14551", "udpout:100.113.116.76:14550", "udpout:100.113.116.76:14556"]
    for port_str in SITL_PORTS:
        conn = None
        try:
            conn = mavutil.mavlink_connection(
                port_str,
                source_system=255
            )
            conn.wait_heartbeat(timeout=2)
            mode_map = conn.mode_mapping()
            if action_str == "FORCE_BRAKE":
                mode_name = "BRAKE"
            elif action_str == "FORCE_RTL":
                mode_name = "RTL"
            else:
                return False

            if mode_map and mode_name in mode_map:
                mode_id = mode_map[mode_name]
                conn.set_mode(mode_id)
                print(f"[MAVLink Direct] ✅ {mode_name} sent via {port_str}")
                return True
            else:
                # Fallback: send DO_SET_MODE command_long
                mode_id = {"BRAKE": 17, "RTL": 6}.get(mode_name, -1)
                if mode_id < 0:
                    continue
                conn.mav.command_long_send(
                    conn.target_system, conn.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                    0,
                    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                    mode_id, 0, 0, 0, 0, 0
                )
                print(f"[MAVLink Direct] ✅ {mode_name} (command_long) sent via {port_str}")
                return True
        except Exception as e:
            print(f"[MAVLink Direct] ⚠️ Connection {port_str} failed: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    print(f"[MAVLink Direct] ❌ All SITL ports exhausted — could not send {action_str}")
    return False

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
    "altitude_m": 0.0,
    "speed_ms": 0.0,
    "ram_load_pct": 0.0,
    "latency_ms": 0,
    "cpu_load_pct": 0.0,
    "latitude": base_lat,
    "longitude": base_lon,
    "vx": 0.0,
    "vy": 0.0,
    "heading": 0.0
}

current_threat_status = "NOMINAL"
current_residual = 1.2
threat_expiry_time = 0.0
last_threat_details = None
last_broadcast_time = 0.0
active_mavlink_ports = set()

async def broadcast_to_websockets(payload: dict):
    """Safely broadcasts a JSON payload to all connected frontend WebSocket clients."""
    for ws in list(active_websockets):
        try:
            await ws.send_json(payload)
        except Exception:
            pass

def compute_and_broadcast_telemetry(source_label: str, loop: asyncio.AbstractEventLoop):
    """Computes dynamic avionics metrics and broadcasts telemetry payload to websockets."""
    global current_threat_status, current_residual, last_broadcast_time
    now = time.time()
    if now - last_broadcast_time < 0.04:  # Throttle to max 25Hz to keep frontend silky smooth
        return
    last_broadcast_time = now

    cur_spd = last_known_telemetry["speed_ms"]
    cur_alt = last_known_telemetry["altitude_m"]
    is_airborne = (cur_alt > 0.4 or cur_spd > 0.2)

    if is_airborne:
        speed_factor = min(cur_spd / 18.0, 1.0)
        cpu_calc = 20.0 + (speed_factor * 34.0) + random.uniform(-0.8, 0.8)
        ram_calc = 32.0 + (speed_factor * 16.0) + random.uniform(-0.4, 0.4)
    else:
        cpu_calc = 15.0 + random.uniform(-0.5, 0.5)
        ram_calc = 30.0 + random.uniform(-0.3, 0.3)

    global threat_expiry_time
    if current_threat_status and "THREAT" in current_threat_status:
        if now >= threat_expiry_time:
            current_threat_status = "NOMINAL"
            current_residual = 1.2
            cpu_calc = min(cpu_calc, 64.0)
            ram_calc = min(ram_calc, 52.0)
        else:
            cpu_calc = min(cpu_calc + 32.0, 79.5)
            ram_calc = min(ram_calc + 15.0, 68.0)
    else:
        cpu_calc = min(cpu_calc, 64.0)
        ram_calc = min(ram_calc, 52.0)

    last_known_telemetry["cpu_load_pct"] = round(cpu_calc, 1)
    last_known_telemetry["ram_load_pct"] = round(ram_calc, 1)
    last_known_telemetry["latency_ms"] = int(random.uniform(9, 15))

    ui_payload = {
        "telemetry": dict(last_known_telemetry),
        "kinematic_residual": current_residual,
        "system_status": current_threat_status,
        "link_connected": True,
        "link_status": f"STREAM_ACTIVE // {source_label}",
        "new_incident": False,
        "incident_details": last_threat_details if now < threat_expiry_time else None
    }
    asyncio.run_coroutine_threadsafe(broadcast_to_websockets(ui_payload), loop)

def mavlink_listener_worker(conn_str: str, loop: asyncio.AbstractEventLoop):
    """
    Dedicated thread listening for ArduPilot SITL / MAVProxy streams.
    Decodes GLOBAL_POSITION_INT, GPS_RAW_INT, VFR_HUD, ATTITUDE, and HEARTBEAT to mirror simulator drone.
    """
    global last_udp_time
    try:
        conn = mavutil.mavlink_connection(conn_str)
        print(f"[MAVLink Ingress] ✅ Connected for SITL/MAVProxy telemetry on {conn_str}...")
        active_mavlink_ports.add(conn_str)
    except Exception as e:
        print(f"[MAVLink Ingress] ⚠️ Note: Connection {conn_str} unavailable ({e})")
        return

    last_stream_req = 0
    while True:
        try:
            msg = conn.recv_match(
                type=['GLOBAL_POSITION_INT', 'GPS_RAW_INT', 'VFR_HUD', 'ATTITUDE', 'HEARTBEAT', 'SYS_STATUS'],
                blocking=True,
                timeout=1.0
            )
            if not msg:
                continue

            msg_type = msg.get_type()
            now = time.time()
            last_udp_time = now

            # Periodically request full telemetry streams at 10Hz
            if now - last_stream_req >= 3.0:
                last_stream_req = now
                try:
                    src_sys = getattr(msg, 'get_srcSystem', lambda: 1)() or 1
                    src_comp = getattr(msg, 'get_srcComponent', lambda: 1)() or 1
                    conn.mav.request_data_stream_send(src_sys, src_comp, mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1)
                    conn.mav.request_data_stream_send(1, 1, mavutil.mavlink.MAV_DATA_STREAM_ALL, 10, 1)
                    for msg_id in [33, 24, 74, 30, 241, 147]:
                        conn.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, msg_id, 100000, 0, 0, 0, 0, 0)
                    conn.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
                except Exception:
                    pass

            if msg_type == 'GLOBAL_POSITION_INT':
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                if abs(lat) > 0.001 and abs(lon) > 0.001:
                    last_known_telemetry["latitude"] = lat
                    last_known_telemetry["longitude"] = lon

                alt_m = msg.relative_alt / 1000.0 if hasattr(msg, 'relative_alt') else msg.alt / 1000.0
                last_known_telemetry["altitude_m"] = round(alt_m, 2)

                vx = msg.vx / 100.0
                vy = msg.vy / 100.0
                vz = msg.vz / 100.0
                last_known_telemetry["vx"] = round(vx, 2)
                last_known_telemetry["vy"] = round(vy, 2)
                last_known_telemetry["vz"] = round(vz, 2)
                if hasattr(msg, 'hdg') and msg.hdg != 65535 and msg.hdg != 0:
                    last_known_telemetry["heading"] = round(msg.hdg / 100.0, 1)

                compute_and_broadcast_telemetry(f"SITL {conn_str}", loop)

            elif msg_type == 'GPS_RAW_INT':
                lat = msg.lat / 1e7
                lon = msg.lon / 1e7
                if abs(lat) > 0.001 and abs(lon) > 0.001:
                    last_known_telemetry["latitude"] = lat
                    last_known_telemetry["longitude"] = lon
                if hasattr(msg, 'alt') and msg.alt != 0:
                    last_known_telemetry["altitude_m"] = round(msg.alt / 1000.0, 2)
                if hasattr(msg, 'vel') and msg.vel != 65535:
                    last_known_telemetry["speed_ms"] = round(msg.vel / 100.0, 2)
                if hasattr(msg, 'cog') and msg.cog != 65535 and msg.cog != 0:
                    last_known_telemetry["heading"] = round(msg.cog / 100.0, 1)

                compute_and_broadcast_telemetry(f"GPS RAW {conn_str}", loop)

            elif msg_type == 'VFR_HUD':
                if hasattr(msg, 'heading') and msg.heading != 0:
                    last_known_telemetry["heading"] = msg.heading
                if hasattr(msg, 'groundspeed'):
                    last_known_telemetry["speed_ms"] = round(msg.groundspeed, 2)
                if hasattr(msg, 'alt'):
                    last_known_telemetry["altitude_m"] = round(msg.alt, 2)

                compute_and_broadcast_telemetry(f"VFR {conn_str}", loop)

            elif msg_type == 'ATTITUDE':
                import math
                if hasattr(msg, 'yaw') and msg.yaw != 0:
                    deg = (math.degrees(msg.yaw) + 360) % 360
                    last_known_telemetry["heading"] = round(deg, 1)

            elif msg_type == 'SYS_STATUS':
                if hasattr(msg, 'load'):
                    last_known_telemetry["cpu_load_pct"] = round(msg.load / 10.0, 1)

            elif msg_type == 'HEARTBEAT':
                compute_and_broadcast_telemetry(f"HEARTBEAT {conn_str}", loop)

        except Exception:
            pass

def simulator_outbound_client_worker(host: str, port: int, loop: asyncio.AbstractEventLoop):
    """
    Proactively connects to ArduPilot SITL / MAVProxy on remote host (Akul) or localhost.
    Sends GCS heartbeat and requests streams so SITL starts streaming telemetry to us.
    """
    global last_udp_time
    while True:
        conn = None
        try:
            conn = mavutil.mavlink_connection(f"udpout:{host}:{port}", source_system=255)
            last_ping = 0
            while True:
                now = time.time()
                if now - last_ping >= 2.0:
                    last_ping = now
                    try:
                        conn.mav.heartbeat_send(
                            mavutil.mavlink.MAV_TYPE_GCS,
                            mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                            0, 0, 0
                        )
                        for msg_id in [33, 24, 74, 30, 241, 147]:
                            conn.mav.command_long_send(1, 1, mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL, 0, msg_id, 100000, 0, 0, 0, 0, 0)
                        conn.mav.request_data_stream_send(
                            1, 1,
                            mavutil.mavlink.MAV_DATA_STREAM_ALL,
                            10, 1
                        )
                    except Exception:
                        pass

                msg = conn.recv_match(
                    type=['GLOBAL_POSITION_INT', 'GPS_RAW_INT', 'VFR_HUD', 'ATTITUDE', 'HEARTBEAT', 'SYS_STATUS'],
                    blocking=True,
                    timeout=1.0
                )
                if not msg:
                    continue

                msg_type = msg.get_type()
                last_udp_time = time.time()

                if msg_type == 'GLOBAL_POSITION_INT':
                    lat = msg.lat / 1e7
                    lon = msg.lon / 1e7
                    if abs(lat) > 0.001 and abs(lon) > 0.001:
                        last_known_telemetry["latitude"] = lat
                        last_known_telemetry["longitude"] = lon
                    alt_m = msg.relative_alt / 1000.0 if hasattr(msg, 'relative_alt') else msg.alt / 1000.0
                    last_known_telemetry["altitude_m"] = round(alt_m, 2)
                    last_known_telemetry["vx"] = round(msg.vx / 100.0, 2)
                    last_known_telemetry["vy"] = round(msg.vy / 100.0, 2)
                    last_known_telemetry["vz"] = round(msg.vz / 100.0, 2)
                    if hasattr(msg, 'hdg') and msg.hdg != 65535 and msg.hdg != 0:
                        last_known_telemetry["heading"] = round(msg.hdg / 100.0, 1)
                    compute_and_broadcast_telemetry(f"SITL OUT {host}:{port}", loop)

                elif msg_type == 'GPS_RAW_INT':
                    lat = msg.lat / 1e7
                    lon = msg.lon / 1e7
                    if abs(lat) > 0.001 and abs(lon) > 0.001:
                        last_known_telemetry["latitude"] = lat
                        last_known_telemetry["longitude"] = lon
                    if hasattr(msg, 'alt') and msg.alt != 0:
                        last_known_telemetry["altitude_m"] = round(msg.alt / 1000.0, 2)
                    if hasattr(msg, 'vel') and msg.vel != 65535:
                        last_known_telemetry["speed_ms"] = round(msg.vel / 100.0, 2)
                    compute_and_broadcast_telemetry(f"GPS RAW {host}:{port}", loop)

                elif msg_type == 'VFR_HUD':
                    if hasattr(msg, 'heading') and msg.heading != 0:
                        last_known_telemetry["heading"] = msg.heading
                    if hasattr(msg, 'groundspeed'):
                        last_known_telemetry["speed_ms"] = round(msg.groundspeed, 2)
                    if hasattr(msg, 'alt'):
                        last_known_telemetry["altitude_m"] = round(msg.alt, 2)
                    compute_and_broadcast_telemetry(f"VFR {host}:{port}", loop)

                elif msg_type == 'HEARTBEAT':
                    compute_and_broadcast_telemetry(f"HEARTBEAT {host}:{port}", loop)

        except Exception:
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
        time.sleep(2.0)

def start_mavlink_listeners(loop: asyncio.AbstractEventLoop):
    candidate_ports = [14550, 14551, 14552, 14554, 14555, 14556, 5760, 69]
    custom_port = os.environ.get("MAVLINK_PORT")
    if custom_port:
        try:
            p = int(custom_port)
            if p not in candidate_ports:
                candidate_ports.insert(0, p)
        except ValueError:
            pass

    # 1. Start inbound listeners on all standard SITL & custom ports
    for p in candidate_ports:
        t = threading.Thread(target=mavlink_listener_worker, args=(f"udpin:0.0.0.0:{p}", loop), daemon=True, name=f"mavlink-in-{p}")
        t.start()
        
    # Add explicit connection to TCP 5762 and 5763 (Akul's SITL instance)
    for p_tcp in [5762, 5763]:
        t_tcp = threading.Thread(target=mavlink_listener_worker, args=(f"tcp:100.113.116.76:{p_tcp}", loop), daemon=True, name=f"mavlink-tcp-{p_tcp}")
        t_tcp.start()

    # 2. Start proactive outbound connector workers to Akul (100.113.116.76) & localhost
    sim_ip = os.environ.get("SIMULATOR_IP", "100.113.116.76")
    for outbound_port in [14550, 14551, 5760]:
        t_out = threading.Thread(
            target=simulator_outbound_client_worker,
            args=(sim_ip, outbound_port, loop),
            daemon=True,
            name=f"mavlink-out-{sim_ip}-{outbound_port}"
        )
        t_out.start()
        # Also local SITL in case running on same machine
        t_local = threading.Thread(
            target=simulator_outbound_client_worker,
            args=("127.0.0.1", outbound_port, loop),
            daemon=True,
            name=f"mavlink-out-local-{outbound_port}"
        )
        t_local.start()

async def secure_receiver_loop():
    """Polls verified UDP packets from Blue Team / M3 Sensor Engine on port 9000."""
    global last_udp_time, current_threat_status, current_residual, threat_expiry_time
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
                    attack_type = (
                        payload.get('attack_type')
                        or payload.get('attack')
                        or payload.get('type')
                        or payload.get('threat')
                        or payload.get('name')
                        or payload.get('alert')
                        or ''
                    )
                    confidence = float(
                        payload.get('confidence')
                        or payload.get('conf')
                        or payload.get('score')
                        or (0.90 if attack_type else 0.0)
                    )

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

                    is_threat = bool(attack_type and confidence >= 0.4)
                    global last_threat_details
                    if is_threat:
                        current_threat_status = f"CRITICAL THREAT INTERCEPTED: {attack_type.upper()}"
                        res = payload.get('kinematic_residual', None)
                        if res is None or float(res) < 16.81:
                            current_residual = round(random.uniform(28.5, 39.8), 2)
                        else:
                            current_residual = round(float(res), 2)
                        threat_expiry_time = time.time() + 8.0
                        residual = current_residual
                        status = current_threat_status
                        last_threat_details = {
                            "type": attack_type,
                            "confidence": confidence,
                            "source": payload.get('source', 'Blue Team M3 Sensor Pipeline'),
                            "failsafe_mode": payload.get('failsafe_mode', 'BRAKE')
                        }
                    else:
                        if time.time() > threat_expiry_time:
                            current_threat_status = "NOMINAL"
                            current_residual = round(float(payload.get('kinematic_residual', random.uniform(0.8, 2.2))), 2)
                            last_threat_details = None
                        residual = current_residual
                        status = current_threat_status

                    ui_payload = {
                        "telemetry": dict(last_known_telemetry),
                        "kinematic_residual": residual,
                        "system_status": status,
                        "link_connected": True,
                        "link_status": "STREAM_ACTIVE",
                        "new_incident": is_threat,
                        "incident_details": last_threat_details if is_threat else (last_threat_details if time.time() < threat_expiry_time else None)
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
                # Telemetry connection lost / waiting for SITL or Blue Team stream
                last_known_telemetry["altitude_m"] = 0.0
                last_known_telemetry["speed_ms"] = 0.0
                last_known_telemetry["vx"] = 0.0
                last_known_telemetry["vy"] = 0.0
                last_known_telemetry["latency_ms"] = 0
                last_known_telemetry["cpu_load_pct"] = 0.0
                last_known_telemetry["ram_load_pct"] = 0.0
                global current_threat_status
                current_threat_status = "NOMINAL"

                heartbeat_payload = {
                    "telemetry": dict(last_known_telemetry),
                    "kinematic_residual": 1.2,
                    "system_status": "LINK_SEVERED",
                    "link_connected": False,
                    "link_status": "DISCONNECTED // SIMULATOR OFFLINE",
                    "new_incident": False
                }

                await broadcast_to_websockets(heartbeat_payload)
        except Exception as e:
            print("[UI Bridge] Link monitor error:", e)

        await asyncio.sleep(0.5)

@app.on_event("startup")
async def startup_event():
    tasks.append(asyncio.create_task(secure_receiver_loop()))
    tasks.append(asyncio.create_task(link_monitor_loop()))
    start_mavlink_listeners(asyncio.get_running_loop())

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
        is_connected = (time.time() - last_udp_time < 3.0) and (last_udp_time > 0)
        await websocket.send_json({
            "telemetry": dict(last_known_telemetry),
            "kinematic_residual": 1.2,
            "system_status": "NOMINAL" if is_connected else "LINK_SEVERED",
            "link_connected": is_connected,
            "link_status": "STREAM_ACTIVE" if is_connected else "DISCONNECTED // SIMULATOR OFFLINE",
            "new_incident": False
        })

        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                action = payload.get("action")
                if action in ("FORCE_BRAKE", "FORCE_RTL"):
                    # Run the blocking MAVLink send in a thread so we don't stall the event loop
                    direct_success = await asyncio.get_event_loop().run_in_executor(
                        None, send_mavlink_direct_command, action
                    )
                    # Also notify Blue Team (best-effort, may fail if they're offline)
                    bt_success = send_secure_command(action)
                    success = direct_success or bt_success
                    route = "SITL Direct" if direct_success else ("Blue Team" if bt_success else "FAILED")
                    await websocket.send_json({
                        "command_confirmation": {
                            "action": action,
                            "success": success,
                            "route": route,
                            "timestamp": time.time(),
                            "message": "Immediate hover-lock command dispatched to flight controller." if action == "FORCE_BRAKE" else "Autonomous return-to-launch command dispatched to flight controller."
                        }
                    })
                elif action == "SIMULATE_ATTACK":
                    # Operator simulation for UI evaluation
                    global current_threat_status, current_residual, threat_expiry_time
                    attack_type = payload.get("type", "velocity_spike")
                    current_threat_status = f"CRITICAL THREAT INTERCEPTED: {attack_type.upper()}"
                    current_residual = round(random.uniform(31.0, 42.0), 2)
                    threat_expiry_time = time.time() + 8.0
                    failsafe = "BRAKE"
                    sim_payload = {
                        "telemetry": dict(last_known_telemetry),
                        "kinematic_residual": current_residual,
                        "system_status": current_threat_status,
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
                    current_threat_status = "NOMINAL"
                    current_residual = 1.2
                    threat_expiry_time = 0.0
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
