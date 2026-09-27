"""
M3 Rule-Based Detection
Loads statistically-derived thresholds from:
  - models/thresholds.json        (attack-specific thresholds)
  - models/phase_thresholds.json  (flight-phase + motion consistency)

Detects 10 M4 attack types using ONLY drone telemetry (no M4 notifications):
  1. GPS spoofing / position offset  → gps_jump, gps_change_rate
  2. GPS freeze                      → motion_consistency
  3. GPS jamming / dropout           → packet_loss_rate, timestamp_max_gap
  4. GPS drift                       → gps_cumulative_drift
  5. Velocity spike                  → velocity_vector_jump
  6. Velocity sweep                  → velocity_oscillation, direction_change_rate
  7. Altitude manipulation           → altitude_drift, altitude_velocity_mismatch
  8. Yaw command hijack              → cmd_yaw_rate_max, cmd_yaw_jump
  9. Command injection               → cmd_mode_changes, cmd_arm_changes,
                                       cmd_param_changes, cmd_ack_rate
 10. Forced takeoff                  → altitude_drift + vertical_speed_mean

Command-level attacks are detected from the drone's RESPONSE
(HEARTBEAT mode changes, COMMAND_ACK echoes, ATTITUDE yaw, PARAM_VALUE)
— M3 does NOT need to see M4's outgoing commands.
"""

import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

ATTACK_THRESHOLD_PATH = os.path.join(PROJECT_ROOT, 'models', 'thresholds.json')
PHASE_THRESHOLD_PATH = os.path.join(PROJECT_ROOT, 'models', 'phase_thresholds.json')

with open(ATTACK_THRESHOLD_PATH, 'r') as f:
    T = json.load(f)

with open(PHASE_THRESHOLD_PATH, 'r') as f:
    PHASE = json.load(f)


def get_threshold(name, default=1e-6):
    """Safe accessor with fallback."""
    return T.get(name, default)


def get_phase(name, default=0.5):
    """Safe accessor for phase thresholds."""
    return PHASE.get(name, default)


def apply_rules(features):
    """
    Apply statistically-derived thresholds.

    Returns list of (attack_type, confidence) tuples.

    Note on absolute thresholds: for spike-type attacks, μ+5σ is too
    aggressive (normal flight has huge velocity variance). We use fixed
    absolute thresholds for those.
    """
    alerts = []

    # ==================== GPS SPOOFING ====================
    if features.get('gps_jump', 0) > get_threshold('gps_jump'):
        alerts.append(('GPS_SPOOFING', 0.90))
    if features.get('gps_cumulative_drift', 0) > get_threshold('gps_cumulative_drift'):
        alerts.append(('GPS_SPOOFING_SLOW', 0.85))
    if features.get('gps_change_rate', 0) > get_threshold('gps_change_rate'):
        alerts.append(('GPS_SPOOFING_FAST', 0.85))

    # ==================== GPS JAMMING ====================
    # Use 5% fixed minimum (data-derived threshold is essentially 0)
    if features.get('packet_loss_rate', 0) > 0.05:
        alerts.append(('GPS_JAMMING', 0.85))
    if features.get('timestamp_max_gap', 0) > get_threshold('timestamp_max_gap'):
        alerts.append(('JAMMING_DETECTED', 0.80))
    if features.get('timestamp_variance', 0) > get_threshold('timestamp_variance'):
        alerts.append(('JAMMING_DETECTED', 0.75))

    # ==================== GPS FREEZE ====================
    # Velocity says moving, GPS shows zero displacement.
    # Requires >1.5 m/s to avoid hover false positives.
    if (features.get('motion_consistency', 1.0) < get_phase('motion_consistency_min')
            and features.get('velocity_magnitude', 0) > 1.5):
        alerts.append(('GPS_FREEZE_ATTACK', 0.90))

    # ==================== CONTROL HIJACK ====================
    if features.get('heading_change', 0) > get_threshold('heading_change'):
        alerts.append(('CONTROL_HIJACK', 0.85))
    if features.get('vz_jump', 0) > get_threshold('vz_jump'):
        alerts.append(('CONTROL_HIJACK', 0.75))
    if features.get('max_velocity_jump', 0) > get_threshold('max_velocity_jump'):
        alerts.append(('SUDDEN_CONTROL', 0.75))

    # ==================== VELOCITY SPIKE ====================
    # Use fixed 5 m/s thresholds — μ+5σ (18.85, 21.53) is too high
    if features.get('max_horizontal_velocity_jump', 0) > 5.0:
        alerts.append(('VELOCITY_SPIKE_HORIZONTAL', 0.85))
    if features.get('velocity_vector_jump', 0) > 5.0:
        alerts.append(('VELOCITY_SPIKE', 0.85))

    # ==================== VELOCITY SWEEP ====================
    if features.get('velocity_oscillation', 0) > get_threshold('velocity_oscillation'):
        alerts.append(('VELOCITY_SWEEP', 0.85))
    if features.get('direction_change_rate', 0) > get_threshold('direction_change_rate'):
        alerts.append(('DIRECTION_HIJACK', 0.80))

    # ==================== ALTITUDE SPOOFING ====================
    if features.get('altitude_drift', 0) > get_threshold('altitude_drift'):
        alerts.append(('ALTITUDE_SPOOFING', 0.80))
    if features.get('altitude_velocity_mismatch', 0) > get_threshold('altitude_velocity_mismatch'):
        alerts.append(('ALTITUDE_SPOOFING', 0.75))

    # ==================== FORCED TAKEOFF ====================
    # Altitude climbing without command during a non-takeoff phase
    if (features.get('altitude_drift', 0) > 5.0
            and features.get('vertical_speed_mean', 0) > 2.0):
        alerts.append(('FORCED_TAKEOFF', 0.85))

    # ==================== COMMAND-LEVEL ATTACKS ====================
    # Detected from the drone's RESPONSE, not M4's outgoing command.

    # arm_disarm: ANY arm/disarm transition during flight is abnormal
    if features.get('cmd_arm_changes', 0) > 0:
        alerts.append(('ARM_DISARM_ATTACK', 0.90))

    # mode_change / land: ANY mode change during flight is suspicious
    if features.get('cmd_mode_changes', 0) >= 1:
        alerts.append(('MODE_CHANGE_ATTACK', 0.85))

    # param_change: any in-flight parameter change
    if features.get('cmd_param_changes', 0) > 0:
        alerts.append(('PARAM_CHANGE_ATTACK', 0.85))

    # command_spam: high rate of COMMAND_ACK echoes from drone
    # (M3 never sees COMMAND_LONG — only the drone's ACKs)
    if features.get('cmd_ack_rate', 0) > 15:
        alerts.append(('COMMAND_SPAM', 0.85))

    # yaw_command: high yaw rate (>90 deg/s) or large yaw jump (>45 deg)
    if features.get('cmd_yaw_rate_max', 0) > 1.57:
        alerts.append(('YAW_HIJACK', 0.85))
    if features.get('cmd_yaw_jump', 0) > 0.79:
        alerts.append(('YAW_HIJACK', 0.80))

    return alerts