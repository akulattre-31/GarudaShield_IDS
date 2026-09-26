"""
Demo MAVLink Sender — Fakes M2's SITL and M4's attacks.
Sends normal telemetry, then injects attacks on a schedule.
"""

import time
import math
import socket
import struct
from pymavlink import mavutil

# ============ CONFIG ============
TARGET_IP = '10.44.73.183'      # Change to your M3 laptop IP if different machine
TARGET_PORT = 14556          # Your runtime engine must listen here
SEND_HZ = 50                 # Messages per second
# ================================

print(f"[Demo] Sending MAVLink to {TARGET_IP}:{TARGET_PORT}")
print(f"[Demo] Rate: {SEND_HZ} Hz")
print("[Demo] Schedule:")
print("  t=0-10s:  NORMAL flight")
print("  t=10-20s: GPS SPOOFING attack")
print("  t=20-25s: NORMAL")
print("  t=25-35s: GPS JAMMING (packet loss)")
print("  t=35-40s: NORMAL")
print("  t=40-50s: DOS FLOOD (2000 Hz)")
print("  t=50-60s: NORMAL")
print("  t=60-70s: COMMAND INJECTION (heading changes)")
print("  t=70+s:   NORMAL")
print()

# Create UDP sender (MAVLink out)
master = mavutil.mavlink_connection(f'udpout:{TARGET_IP}:{TARGET_PORT}')

# Baseline state
lat = -35.3632620
lon = 149.1652372
alt_m = 634.0
vx = 0.01
vy = 0.02
vz = -2.5
heading_rad = 0.0
boot_time = time.time()


def send_normal_gps():
    """Send normal GLOBAL_POSITION_INT."""
    master.mav.global_position_int_send(
        int((time.time() - boot_time) * 1000),  # time_boot_ms
        int(lat * 1e7),
        int(lon * 1e7),
        int(alt_m * 1000),
        int(alt_m * 1000),    # relative_alt
        int(vx * 100),
        int(vy * 100),
        int(vz * 100),
        int(heading_rad * 100 * 57.3)
    )


def send_spoofed_gps(offset_m=500):
    """Send GPS jumped 500m away."""
    fake_lat = lat + (offset_m / 111320.0)
    master.mav.global_position_int_send(
        int((time.time() - boot_time) * 1000),
        int(fake_lat * 1e7),   # ← spoofed latitude
        int(lon * 1e7),
        int(alt_m * 1000),
        int(alt_m * 1000),
        int(vx * 100),
        int(vy * 100),
        int(vz * 100),
        int(heading_rad * 100 * 57.3)
    )


def send_imu():
    """Send RAW_IMU to feed EKF."""
    master.mav.raw_imu_send(
        int((time.time() - boot_time) * 1000),
        0, 0, -9800,           # xacc, yacc, zacc
        int(vx * 100), int(vy * 100), int(vz * 100),   # xgyro, ygyro, zgyro
        0, 0, 1000             # xmag, ymag, zmag
    )


def send_heartbeat():
    master.mav.heartbeat_send(
        mavutil.mavlink.MAV_TYPE_QUADROTOR,
        mavutil.mavlink.MAV_AUTOPILOT_ARDUPILOTMEGA,
        0, 0, 0
    )


# Send initial heartbeat to establish connection
send_heartbeat()
send_imu()
send_normal_gps()
time.sleep(0.5)

last_status = time.time()
last_normal = time.time()

try:
    while True:
        now = time.time()
        elapsed = now - boot_time

        # ---- STATUS PRINT ----
        if now - last_status > 5:
            print(f"[Demo] t={elapsed:.0f}s | phase: ", end='')
            if elapsed < 10:
                print("NORMAL")
            elif elapsed < 20:
                print("GPS SPOOF ATTACK")
            elif elapsed < 25:
                print("NORMAL")
            elif elapsed < 35:
                print("GPS JAMMING")
            elif elapsed < 40:
                print("NORMAL")
            elif elapsed < 50:
                print("DOS FLOOD")
            elif elapsed < 60:
                print("NORMAL")
            elif elapsed < 70:
                print("CMD INJECTION")
            else:
                print("NORMAL")
            last_status = now

        # ---- HEARTBEAT every 1s ----
        if int(elapsed * SEND_HZ) % SEND_HZ == 0:
            send_heartbeat()

        # ---- SCENARIO LOGIC ----
        if elapsed < 10:
            # Normal
            send_imu()
            send_normal_gps()

        elif elapsed < 20:
            # GPS SPOOF: send IMU (normal) but GPS jumps +500m
            send_imu()
            send_spoofed_gps(offset_m=500)

        elif elapsed < 25:
            # Normal
            send_imu()
            send_normal_gps()

        elif elapsed < 35:
            # GPS JAMMING: skip GPS messages, only send IMU
            # This will make packet_loss_rate spike in M3
            send_imu()
            # Skip GPS sends intentionally

        elif elapsed < 40:
            # Normal
            send_imu()
            send_normal_gps()

        elif elapsed < 50:
            # DOS FLOOD: send 2000 messages/sec
            for _ in range(40):
                send_imu()
                send_normal_gps()

        elif elapsed < 60:
            # Normal
            send_imu()
            send_normal_gps()

        elif elapsed < 70:
            # COMMAND INJECTION: sudden heading changes
            heading_rad += 0.5   # rapid heading change
            send_imu()
            send_normal_gps()

        else:
            # Normal
            send_imu()
            send_normal_gps()

        time.sleep(1.0 / SEND_HZ)

except KeyboardInterrupt:
    print("\n[Demo] Stopped")
