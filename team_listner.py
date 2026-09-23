import sys
from pymavlink import mavutil

PORT = 14551 

connection_string = f'udpin:0.0.0.0:{PORT}'

print(f"GarudaShield Live Sync: Listening on port {PORT}...")
try:
    connection = mavutil.mavlink_connection(connection_string)
    connection.wait_heartbeat()
    print(f"Connection Established! Syncing with Drone ID: {connection.target_system}\n")
    
    while True:
        # Listen exclusively for the physical telemetry packets
        msg = connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        
        if msg:
            # Decode the raw MAVLink data into human-readable engineering units
            lat = msg.lat / 1e7
            lon = msg.lon / 1e7
            alt_m = msg.alt / 1000.0
            vx = msg.vx / 100.0
            vy = msg.vy / 100.0
            vz = msg.vz / 100.0
            
            # Print the live telemetry feed directly to the terminal on a single refreshing line
            sys.stdout.write(f"\r📍 Pos: [{lat:.5f}, {lon:.5f}] | ⛰️ Alt: {alt_m:.2f}m | 🚀 Spd: X:{vx:.2f} Y:{vy:.2f} Z:{vz:.2f}")
            sys.stdout.flush()

except KeyboardInterrupt:
    print("\n\nLive sync terminated.")
except PermissionError:
    print(f"\n\n[ERROR] Permission denied on port {PORT}.")
    print("If you are using a privileged port like 69, run this script using 'sudo python3 team_listener.py'")
