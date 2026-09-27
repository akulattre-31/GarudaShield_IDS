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

RULE_MIN_CONFIDENCE = 0.70   # rule/ekf/seq_validator/rate_limiter detections
ML_MIN_CONFIDENCE = 0.90     # ML unknown-anomaly detections

# ArduCopter custom mode IDs
MODE_RTL = 6
MODE_LAND = 9
MODE_BRAKE = 17

# Attack → failsafe mode mapping
# Rationale:
#   BRAKE — stop motion, hold position, don't trust compromised sensor
#   LAND  — get on ground ASAP (critical or unrecoverable attacks)
#   RTL   — fly home (GPS lost but IMU still reliable)
FAILSAFE_MAP = {
    # --- Sensor attacks (stop, don't trust inputs) ---
    'GPS_SPOOFING_ALERT':        ('BRAKE', MODE_BRAKE),
    'GPS_SPOOFING':              ('BRAKE', MODE_BRAKE),
    'GPS_SPOOFING_SLOW':         ('BRAKE', MODE_BRAKE),
    'GPS_SPOOFING_FAST':         ('BRAKE', MODE_BRAKE),
    'GPS_FREEZE_ATTACK':         ('BRAKE', MODE_BRAKE),
    'ALTITUDE_SPOOFING':         ('BRAKE', MODE_BRAKE),

    # --- Command injection (immediate stop) ---
    'ARM_DISARM_ATTACK':         ('BRAKE', MODE_BRAKE),
    'MODE_CHANGE_ATTACK':        ('BRAKE', MODE_BRAKE),
    'PARAM_CHANGE_ATTACK':       ('BRAKE', MODE_BRAKE),
    'COMMAND_SPAM':              ('BRAKE', MODE_BRAKE),

    # --- Control hijack (stop motion) ---
    'CONTROL_HIJACK':            ('BRAKE', MODE_BRAKE),
    'SUDDEN_CONTROL':            ('BRAKE', MODE_BRAKE),
    'YAW_HIJACK':                ('BRAKE', MODE_BRAKE),
    'VELOCITY_SPIKE':            ('BRAKE', MODE_BRAKE),
    'VELOCITY_SPIKE_HORIZONTAL': ('BRAKE', MODE_BRAKE),
    'VELOCITY_SWEEP':            ('BRAKE', MODE_BRAKE),
    'DIRECTION_HIJACK':          ('BRAKE', MODE_BRAKE),

    # --- DoS flood (protect autopilot, land) ---
    'DOS_FLOOD_ALERT':           ('LAND', MODE_LAND),

    # --- Forced takeoff (dangerous, bring down) ---
    'FORCED_TAKEOFF':            ('LAND', MODE_LAND),

    # --- GPS jamming (fly home on IMU) ---
    'GPS_JAMMING':               ('RTL', MODE_RTL),
    'JAMMING_DETECTED':          ('RTL', MODE_RTL),

    # --- Rogue injection (severe) ---
    'ROGUE_INJECTION_ALERT':     ('LAND', MODE_LAND),

    # --- Unknown ML anomaly ---
    'UNKNOWN_ANOMALY':           ('BRAKE', MODE_BRAKE),
}


def dispatch_failsafe(master, attack_type, confidence, source='rule'):
    """
    Send MAV_CMD_DO_SET_MODE to drone when an attack is detected.

    `source` is the detector that raised the alert ('rule', 'ekf',
    'seq_validator', 'rate_limiter', or 'ml') and picks which confidence
    threshold applies — see module docstring.

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

    if attack_type not in FAILSAFE_MAP:
        print(f"[Mitigation] ❓ No failsafe mapped for {attack_type}")
        return False

    mode_name, mode_id = FAILSAFE_MAP[attack_type]
    t0 = time.time()

    print(f"[Mitigation] 🚨 Dispatching {mode_name} for {attack_type}")

    try:
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