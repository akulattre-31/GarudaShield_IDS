import asyncio
import json
import time
import random
import math
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn

# Import the Blue Team's secure transport
from secure_transport import SecureReceiver, SecureSender

app = FastAPI()

frontend_path = "/home/om/Projects/work/drone/frontend"
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def get_index():
    return RedirectResponse(url="/static/index.html")

# ==========================================
# SECURE PIPELINE CONFIGURATION
# ==========================================
BLUE_TEAM_IP = "100.126.113.10"
COMMAND_PORT = 9002
LISTEN_PORT = 9000

# Initialize secure sender and receiver
secure_receiver = SecureReceiver('0.0.0.0', LISTEN_PORT, max_age_sec=60)
secure_sender = SecureSender(BLUE_TEAM_IP, COMMAND_PORT)

active_websockets = set()
last_udp_time = 0
tasks = []

def send_secure_command(action_str):
    try:
        payload = {"action": action_str, "timestamp": time.time()}
        secure_sender.send(payload)
        print(f"[UI Bridge] Sent secure command to Blue Team ({BLUE_TEAM_IP}): {action_str}")
    except Exception as e:
        print("[UI Bridge] Failed to send secure command:", e)

# ==========================================
# MOCK DATA FOR DEMO CONTINUITY
# ==========================================
start_time = time.time()
base_lat = -35.363262
base_lon = 149.165237

def generate_mock_telemetry():
    t = time.time() - start_time
    radius = 0.005
    angular_speed = 0.1
    current_lat = base_lat + radius * math.sin(t * angular_speed)
    current_lon = base_lon + radius * math.cos(t * angular_speed)
    vx = radius * angular_speed * math.cos(t * angular_speed) * 111000 
    vy = -radius * angular_speed * math.sin(t * angular_speed) * 111000

    return {
        "telemetry": {
            "altitude_m": 150.0 + 10.0 * math.sin(t * 0.5),
            "speed_ms": math.sqrt(vx**2 + vy**2) / 10.0,  
            "ram_load_pct": 45.0 + random.random() * 5.0,
            "latency_ms": int(10 + random.random() * 5),
            "cpu_load_pct": 30.0 + random.random() * 10.0,
            "latitude": current_lat,
            "longitude": current_lon,
            "vx": vx / 10.0,
            "vy": vy / 10.0
        },
        "kinematic_residual": random.random() * 2.0,
        "system_status": "NOMINAL"
    }

async def secure_receiver_loop():
    global last_udp_time
    print(f"[UI Bridge] Listening for secure alerts on UDP {LISTEN_PORT}...")
    while True:
        try:
            # Poll the secure receiver non-blocking
            verified_payloads = secure_receiver.poll()
            for payload in verified_payloads:
                last_udp_time = time.time()
                # Broadcast the securely verified payload to the UI
                for ws in list(active_websockets):
                    asyncio.create_task(ws.send_json(payload))
        except Exception as e:
            print("[UI Bridge] Receiver error:", e)
        
        await asyncio.sleep(0.05) # ~20Hz poll rate

async def mock_telemetry_loop():
    while True:
        # If no secure data received in the last 2 seconds, send mock to keep UI alive
        if time.time() - last_udp_time >= 2:
            mock_data = generate_mock_telemetry()
            for ws in list(active_websockets):
                try:
                    await ws.send_json(mock_data)
                except Exception:
                    pass
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    # Start the background polling loops
    tasks.append(asyncio.create_task(secure_receiver_loop()))
    tasks.append(asyncio.create_task(mock_telemetry_loop()))

@app.on_event("shutdown")
async def shutdown_event():
    for task in tasks:
        task.cancel()

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if "action" in payload:
                    send_secure_command(payload["action"])
            except Exception as e:
                print("Error parsing ws data:", e)
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
    except Exception as e:
        if websocket in active_websockets:
            active_websockets.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
