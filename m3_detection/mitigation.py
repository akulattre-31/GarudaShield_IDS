"""
M3 Mitigation
Autonomous failsafe dispatch.
"""

import time
from pymavlink import mavutil

# Safety flag: set to False to disable failsafe during testing
ENABLE_FAILSAFE = False


def dispatch_failsafe(master, attack_type, confidence):
    if not ENABLE_FAILSAFE:
        print(f"[Mitigation] DISABLED (would dispatch for {attack_type})")
        return False

    if confidence < 0.90:
        return False

    t0 = time.time()

    if attack_type in ('GPS_SPOOFING_ALERT', 'CONTROL_HIJACK', 'ROGUE_INJECTION_ALERT'):
        mode_name = 'BRAKE'
        mode_id = 17
    elif attack_type in ('DOS_FLOOD_ALERT',):
        mode_name = 'LAND'
        mode_id = 9
    else:
        return False

    print(f"[Mitigation] 🚨 Dispatching failsafe: {mode_name}")

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_CMD_DO_SET_MODE,
        0,
        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
        mode_id,
        0, 0, 0, 0, 0
    )

    latency_ms = (time.time() - t0) * 1000
    print(f"[Mitigation] Failsafe in {latency_ms:.1f} ms")
    return True