import csv
import random
from pymavlink import mavutil

# Connect to M2's local UDP port (Default MAVProxy output)
connection = mavutil.mavlink_connection('udpin:127.0.0.1:14550')

print("GarudaShield M2 Logger: Waiting for drone heartbeat...")
connection.wait_heartbeat()
print(f"Connected to drone! System ID: {connection.target_system}")
print("Recording live telemetry with network jitter to flight_data.csv...")
print("Press Ctrl+C to stop recording and save the file.")

try:
    # Open the CSV file in write mode
    with open('flight_data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        
        # Write the header row exactly as expected by M3's detection engine
        writer.writerow(['timestamp_ms', 'latitude', 'longitude', 'altitude_m', 'vx', 'vy', 'vz'])
        
        while True:
            # Catch the GLOBAL_POSITION_INT MAVLink message
            msg = connection.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
            
            if msg:
                # Inject realistic network delay (-5ms to +5ms) to prevent zero-variance
                jitter = random.randint(-5, 5)
                timestamp_jittered = msg.time_boot_ms + jitter
                
                # Format the raw MAVLink data into standard units and write to the CSV
                writer.writerow([
                    timestamp_jittered, 
                    msg.lat / 1e7,      # Convert latitude to standard degrees
                    msg.lon / 1e7,      # Convert longitude to standard degrees
                    msg.alt / 1000.0,   # Convert altitude from millimeters to meters
                    msg.vx / 100.0,     # Convert X velocity from cm/s to m/s
                    msg.vy / 100.0,     # Convert Y velocity from cm/s to m/s
                    msg.vz / 100.0      # Convert Z velocity from cm/s to m/s
                ])
                
except KeyboardInterrupt:
    print("\n[M2] Logging stopped. Dataset successfully saved to flight_data.csv.")
