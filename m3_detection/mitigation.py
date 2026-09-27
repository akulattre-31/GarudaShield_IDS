"""
M3 Mitigation — Autonomous Failsafe Dispatch

Maps every detected attack to an appropriate ArduCopter flight mode:
  BRAKE (17) — stop in place, hold position (best for sensor attacks)
  LAND  (9)  — land immediately in place (best for critical)
  RTL   (6)  — return to launch using IMU dead-reckoning (for GPS attacks)

Failsafe dispatch is gated by confidence, but the bar differs by detector
source:
  - 'rule', 'ekf', 'seq_validator', 'rate_limiter' are deterministic
    threshold-crosses. Their "confidence" is a hand-tuned severity label
    (rules.py assigns 0.75-0.95 depending on how certain that specific
    check is), not a calibrated probability — so these are trusted at a
    lower bar (RULE_MIN_CONFIDENCE).
  - 'ml' (the Isolation Forest UNKNOWN_ANOMALY path) is a genuine
    probabilistic anomaly score on patterns never seen before, so it
    stays gated higher (ML_MIN_CONFIDENCE) before we let it force a
    flight-mode change.
Controlled by ENABLE_FAILSAFE flag (set True for demo, False for testing).
"""

import time
from pymavlink import mavutil

# Safety flag: set to False during development, True during demo
ENABLE_FAILSAFE = True

RULE_MIN_CONFIDENCE = 0.50   # rule/ekf/seq_validator/rate_limiter detections
ML_MIN_CONFIDENCE = 0.50     # ML unknown-anomaly detections (aligned with runtime engine gate)

# ArduCopter custom mode IDs
MODE_RTL = 6
MODE_LAND = 9
MODE_BRAKE = 17

# Attack → failsafe mode mapping
# Autonomous defense policy: Dispatch BRAKE (17) for all detected attack vectors
# to immediately stop motion and freeze the drone in a stable optical/inertial hover.
FAILSAFE_MAP = {
    # --- Sensor attacks (stop, don't trust inputs) ---
    'GPS_SPOOFING_ALERT':        ('BRAKE', MODE_BRAKE),
    'GPS_SPOOFING':              ('BRAKE', MODE_BRAKE),
    'GPS_SPOOFING_SLOW':         ('BRAKE', MODE_BRAKE),
    'GPS_SPOOFING_FAST':         ('BRAKE', MODE_BRAKE),
    'GPS_FREEZE_ATTACK':         ('BRAKE', MODE_BRAKE),
    'ALTITUDE_SPOOFING':         ('BRAKE', MODE_BRAKE),

    # --- Command injection & discrete overrides (immediate stop) ---
    'ARM_DISARM_ATTACK':         ('BRAKE', MODE_BRAKE),
    'ARM_DISARM':                ('BRAKE', MODE_BRAKE),
    'MODE_CHANGE_ATTACK':        ('BRAKE', MODE_BRAKE),
    'MODE_CHANGE':               ('BRAKE', MODE_BRAKE),
    'PARAM_CHANGE_ATTACK':       ('BRAKE', MODE_BRAKE),
    'PARAMETER_CHANGE':          ('BRAKE', MODE_BRAKE),
    'COMMAND_SPAM':              ('BRAKE', MODE_BRAKE),

    # --- Control & Trajectory Hijacks (stop motion) ---
    'CONTROL_HIJACK':            ('BRAKE', MODE_BRAKE),
    'SUDDEN_CONTROL':            ('BRAKE', MODE_BRAKE),
    'YAW_HIJACK':                ('BRAKE', MODE_BRAKE),
    'YAW_COMMAND':               ('BRAKE', MODE_BRAKE),
    'VELOCITY_SPIKE':            ('BRAKE', MODE_BRAKE),
    'VELOCITY_SPIKE_HORIZONTAL': ('BRAKE', MODE_BRAKE),
    'VELOCITY_SWEEP':            ('BRAKE', MODE_BRAKE),
    'DIRECTION_HIJACK':          ('BRAKE', MODE_BRAKE),
    'POSITION_OFFSET':           ('BRAKE', MODE_BRAKE),

    # --- DoS flood & critical commands ---
    'DOS_FLOOD_ALERT':           ('BRAKE', MODE_BRAKE),
    'FORCED_TAKEOFF':            ('BRAKE', MODE_BRAKE),
    'TAKEOFF':                   ('BRAKE', MODE_BRAKE),
    'LAND':                      ('BRAKE', MODE_BRAKE),
    'ROGUE_LAND':                ('BRAKE', MODE_BRAKE),
    'LAND_HIJACK':               ('BRAKE', MODE_BRAKE),

    # --- GPS jamming & rogue injection ---
    'GPS_JAMMING':               ('BRAKE', MODE_BRAKE),
    'JAMMING_DETECTED':          ('BRAKE', MODE_BRAKE),
    'ROGUE_INJECTION_ALERT':     ('BRAKE', MODE_BRAKE),

    # --- Unknown ML anomaly ---
    'UNKNOWN_ANOMALY':           ('BRAKE', MODE_BRAKE),
}


def dispatch_failsafe(master, attack_type, confidence, source='rule'):
    """
    Send MAVLink BRAKE mode command to drone when an attack is detected.

    `source` is the detector that raised the alert ('rule', 'ekf',
    'seq_validator', 'rate_limiter', or 'ml').

    Returns:
      (mode_name, mode_id) if dispatched
      False otherwise
    """
    if not ENABLE_FAILSAFE:
        print(f"[Mitigation] ⏸  DISABLED (would dispatch for {attack_type})")
        return False

    min_confidence = ML_MIN_CONFIDENCE if source == 'ml' else RULE_MIN_CONFIDENCE
    if confidence < min_confidence:
        print(f"[Mitigation] ⏭  Skipped (confidence {confidence:.2f} < "
              f"{min_confidence:.2f} for source={source})")
        return False

    # Standardize attack type key or default to BRAKE
    normalized_type = str(attack_type).strip().upper()
    mode_name, mode_id = FAILSAFE_MAP.get(normalized_type, FAILSAFE_MAP.get(attack_type, ('BRAKE', MODE_BRAKE)))
    t0 = time.time()

    print(f"[Mitigation] 🚨 Dispatching {mode_name} for {attack_type}")

    try:
        # 1. Primary path: MAVLink set_mode_send
        master.mav.set_mode_send(
            master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id
        )
        # 2. Secondary path: MAV_CMD_DO_SET_MODE command_long
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_DO_SET_MODE,
            0,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id,
            0, 0, 0, 0, 0
        )
    except Exception as e:
        print(f"[Mitigation] ❌ Send failed: {e}")
        return False

    latency_ms = (time.time() - t0) * 1000
    print(f"[Mitigation] ✅ {mode_name} sent in {latency_ms:.1f} ms")
    return (mode_name, mode_id)