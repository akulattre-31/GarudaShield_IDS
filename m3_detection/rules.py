"""
M3 Rules Engine — live detection
=================================
Reads thresholds from models/thresholds.json (level-flight derived) and
models/phase_thresholds.json. Returns (attack_type, confidence) tuples.

Design decisions documented inline.
"""

import os
import json

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

THRESHOLDS_PATH = os.path.join(PROJECT_ROOT, 'models', 'thresholds.json')
PHASE_PATH      = os.path.join(PROJECT_ROOT, 'models', 'phase_thresholds.json')


def _load(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

_TH = _load(THRESHOLDS_PATH)
_PH = _load(PHASE_PATH)


# --- FIX ---
# Physical floors. Runtime windows are ~1 s vs. 2.5 s in training, so
# diff-of-adjacent-sample statistics do not transfer exactly. The floors
# prevent the rule from firing below the physical noise floor regardless
# of what the derived threshold says.
_FLOORS = {
    'max_horizontal_velocity_jump': 0.5,
    'velocity_vector_jump':         1.0,
    'vx_jump':                      0.5,
    'vy_jump':                      0.5,
    'vz_jump':                      0.5,
    # packet_loss_rate is 0 (zero variance) on a localhost SITL link, so
    # a derived mean+5sigma threshold can collapse to ~1e-6. Without a
    # floor, GPS_JAMMING fires on the first packet that's even slightly
    # delayed over a real radio/WiFi link. Kept in sync with the
    # DEGENERATE_FALLBACK value in derive_thresholds.py.
    'packet_loss_rate':             0.15,
}

_FALLBACK_TH = {
    'gps_jump':                       5.0e-5,
    'gps_change_rate':                5.0e-6,
    'motion_consistency':             0.40,
    'vx_jump':                        0.7,
    'vy_jump':                        1.2,
    'vz_jump':                        1.2,
    'max_horizontal_velocity_jump':   1.0,
    'velocity_vector_jump':           1.5,
    'max_velocity_jump':              1.0,
    'velocity_oscillation':           0.5,
    'direction_change_rate':          0.3,
    'altitude_velocity_mismatch':     15.0,
    'packet_loss_rate':               0.20,
}
_FALLBACK_PH = {
    'motion_consistency_min':         0.35,
    'moving_speed_min':               0.5,
}


def _th(name):
    v = _TH.get(name, _FALLBACK_TH.get(name, 0.0))
    if name in _FLOORS:
        v = max(v, _FLOORS[name])
    return v


def _ph(name):
    return _PH.get(name, _FALLBACK_PH.get(name, 0.0))


# ----------------------------------------------------------------------
def apply_rules(features):
    alerts = []

    # ==================================================================
    # 1) VELOCITY SPIKE
    # ==================================================================
    horiz_jump = features.get('max_horizontal_velocity_jump', 0.0)
    vec_jump   = features.get('velocity_vector_jump', 0.0)
    vx_jump    = features.get('vx_jump', 0.0)
    vy_jump    = features.get('vy_jump', 0.0)
    vz_jump    = features.get('vz_jump', 0.0)

    h_th = _th('max_horizontal_velocity_jump')
    v_th = _th('velocity_vector_jump')
    z_th = _th('vz_jump')

    if horiz_jump > h_th * 3.0 or (vx_jump > h_th * 2.0 and vy_jump > h_th * 2.0):
        alerts.append(('VELOCITY_SPIKE_HORIZONTAL', 0.95))
    elif horiz_jump > h_th * 2.0 and vec_jump > v_th:
        alerts.append(('VELOCITY_SPIKE_HORIZONTAL', 0.85))
    elif vec_jump > v_th * 2.0:
        alerts.append(('VELOCITY_SPIKE', 0.90))
    elif vz_jump > z_th * 3.0:
        alerts.append(('VELOCITY_SPIKE', 0.85))

    # ==================================================================
    # 2) VELOCITY SWEEP
    # ==================================================================
    osc = features.get('velocity_oscillation', 0.0)
    dcr = features.get('direction_change_rate', 0.0)

    osc_th = _th('velocity_oscillation')
    dcr_th = _th('direction_change_rate')

    if osc > osc_th * 2.0 and dcr > dcr_th * 2.0:
        alerts.append(('VELOCITY_SWEEP', 0.95))
    elif osc > osc_th and dcr > dcr_th:
        alerts.append(('VELOCITY_SWEEP', 0.80))

    # ==================================================================
    # 3) DIRECTION HIJACK
    # ==================================================================
    if features.get('heading_change', 0.0) > 2.5:
        alerts.append(('DIRECTION_HIJACK', 0.85))

    # ==================================================================
    # 4) GPS SPOOFING
    # ==================================================================
    gps_jump = features.get('gps_jump', 0.0)
    gps_th   = _th('gps_jump')

    if gps_jump > gps_th * 3.0:
        alerts.append(('GPS_SPOOFING_FAST', 0.95))
    elif gps_jump > gps_th:
        alerts.append(('GPS_SPOOFING_SLOW', 0.85))

    # ==================================================================
    # 5) GPS FREEZE
    # ==================================================================
    mc    = features.get('motion_consistency', 1.0)
    hvel  = features.get('horizontal_speed', 0.0)
    mc_th = _ph('motion_consistency_min')

    if mc < mc_th and hvel > 1.5:
        alerts.append(('GPS_FREEZE_ATTACK', 0.90))

    # ==================================================================
    # 6) ALTITUDE SPOOFING
    # ==================================================================
    if features.get('altitude_velocity_mismatch', 0.0) > _th('altitude_velocity_mismatch'):
        alerts.append(('ALTITUDE_SPOOFING', 0.85))

    # ==================================================================
    # 7) COMMAND-LEVEL attacks
    # ==================================================================
    if features.get('cmd_arm_changes', 0) > 0:
        alerts.append(('ARM_DISARM_ATTACK', 0.90))
    if features.get('cmd_mode_changes', 0) > 0:
        alerts.append(('MODE_CHANGE_ATTACK', 0.90))
    if features.get('cmd_param_changes', 0) >= 1:
        alerts.append(('PARAM_CHANGE_ATTACK', 0.85))
    if features.get('cmd_ack_rate', 0) >= 8:
        alerts.append(('COMMAND_SPAM', 0.85))
    if features.get('cmd_yaw_rate_max', 0.0) > 1.2 or features.get('cmd_yaw_jump', 0.0) > 1.0:
        alerts.append(('YAW_HIJACK', 0.85))

    # ==================================================================
    # 8) POSITION OFFSET & Jamming
    # ==================================================================
    if features.get('gps_jump_m', 0.0) > 3.0:
        alerts.append(('POSITION_OFFSET', 0.85))
    if features.get('packet_loss_rate', 0.0) > _th('packet_loss_rate'):
        alerts.append(('GPS_JAMMING', 0.80))

    return alerts