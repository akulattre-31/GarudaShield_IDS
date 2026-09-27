"""
M3 Rules Engine
Threshold-based detection for known attacks, using data-derived
thresholds from models/thresholds.json + flight-phase awareness
from models/phase_thresholds.json.

Returns a list of (attack_type, confidence) tuples.

Design notes (anti-FP):
  - Every numeric threshold is the *statistical* boundary from
    derive_thresholds.py (μ+5σ, or 99th percentile for heavy-tailed
    features). Crossing one of these is already rare on normal flight.
  - Velocity-sweep requires BOTH oscillation and direction-flip to
    fire, so a single gust/side-wind bump won't trigger it.
  - Single-window spikes fire at ≥0.90 confidence so that the
    CONFIRM_WINDOWS gate in runtime_engine confirms them cleanly
    (3 consecutive windows) instead of flapping.
"""

import os
import json

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
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


def _t(name, default):
    """Threshold lookup with sane fallbacks if thresholds.json is missing."""
    return _TH.get(name, default)


# Sensible defaults in case derive_thresholds.py hasn't been run yet.
DEFAULTS = {
    'gps_jump':                       5.0e-5,
    'gps_change_rate':                5.0e-6,
    'motion_consistency':             0.20,
    'vx_jump':                        1.0,
    'vy_jump':                        1.0,
    'vz_jump':                        1.0,
    'max_horizontal_velocity_jump':   1.2,
    'velocity_vector_jump':           1.5,
    'max_velocity_jump':              1.5,
    'velocity_oscillation':           0.5,
    'direction_change_rate':          0.3,
    'altitude_velocity_mismatch':     5.0,
    'packet_loss_rate':               0.20,
}


def _th(name):
    return _t(name, DEFAULTS.get(name, 0.0))


# ----------------------------------------------------------------------
def apply_rules(features):
    """
    features: dict produced by runtime_engine.extract_from_window,
              including the 7 merged cmd_* keys from CommandMonitor.
    Returns:  list of (attack_type, confidence)
    """
    alerts = []

    phase = features.get('_phase', 'unknown')

    # ------------------------------------------------------------------
    # 1) VELOCITY SPIKE  (sudden large change in the velocity vector)
    # ------------------------------------------------------------------
    # Two severities:
    #   - horizontal spike is the typical injection pattern
    #   - 3D vector spike covers vertical-too cases
    # A 1.5× margin over the μ+5σ threshold is required for the
    # higher-confidence flag so normal turbulence doesn't trip it.
    horiz_jump = features.get('max_horizontal_velocity_jump', 0.0)
    vec_jump   = features.get('velocity_vector_jump', 0.0)
    vx_jump    = features.get('vx_jump', 0.0)
    vy_jump    = features.get('vy_jump', 0.0)
    vz_jump    = features.get('vz_jump', 0.0)

    h_th = _th('max_horizontal_velocity_jump')
    v_th = _th('velocity_vector_jump')
    z_th = _th('vz_jump')

    # Hover is the most sensitive phase — even a modest jump is anomalous
    # when the drone was supposed to be sitting still.
    sensitivity = 0.7 if phase == 'hover' else 1.0

    if horiz_jump > h_th * 1.5 * sensitivity or (vx_jump > h_th and vy_jump > h_th):
        alerts.append(('VELOCITY_SPIKE_HORIZONTAL', 0.95))
    elif horiz_jump > h_th * sensitivity:
        alerts.append(('VELOCITY_SPIKE_HORIZONTAL', 0.85))
    elif vec_jump > v_th * sensitivity:
        alerts.append(('VELOCITY_SPIKE', 0.90))
    elif vz_jump > z_th * 1.5:
        # vertical-only sudden jump — covered by ALTITUDE_SPOOFING too,
        # but classify it here as a velocity-domain spike.
        alerts.append(('VELOCITY_SPIKE', 0.85))

    # ------------------------------------------------------------------
    # 2) VELOCITY SWEEP  (sustained oscillation / weaving)
    # ------------------------------------------------------------------
    # Requires BOTH features to exceed their (already 99th-percentile)
    # thresholds — one alone is too easy to trigger on a gust.
    osc = features.get('velocity_oscillation', 0.0)
    dcr = features.get('direction_change_rate', 0.0)

    osc_th = _th('velocity_oscillation')
    dcr_th = _th('direction_change_rate')

    if osc > osc_th * 2.0 and dcr > dcr_th * 2.0:
        alerts.append(('VELOCITY_SWEEP', 0.95))
    elif osc > osc_th and dcr > dcr_th:
        alerts.append(('VELOCITY_SWEEP', 0.80))

    # ------------------------------------------------------------------
    # 3) DIRECTION HIJACK  (large heading change while moving)
    # ------------------------------------------------------------------
    # ~115° in one window ≈ 2.0 rad. Only meaningful if the drone was
    # actually moving — extract_from_window already zeroes heading_change
    # when horizontal speed < moving_speed_min, so no extra guard needed.
    if features.get('heading_change', 0.0) > 2.0:
        alerts.append(('DIRECTION_HIJACK', 0.85))

    # ------------------------------------------------------------------
    # 4) GPS attacks  (spoofing / freeze)
    # ------------------------------------------------------------------
    gps_jump = features.get('gps_jump', 0.0)
    gps_jump_th = _th('gps_jump')
    if gps_jump > gps_jump_th * 3.0:
        alerts.append(('GPS_SPOOFING_FAST', 0.95))
    elif gps_jump > gps_jump_th:
        alerts.append(('GPS_SPOOFING_SLOW', 0.85))

    if features.get('motion_consistency', 1.0) < _th('motion_consistency'):
        alerts.append(('GPS_FREEZE_ATTACK', 0.90))

    # ------------------------------------------------------------------
    # 5) ALTITUDE SPOOFING  (altitude/velocity cross-check mismatch)
    # ------------------------------------------------------------------
    if features.get('altitude_velocity_mismatch', 0.0) > _th('altitude_velocity_mismatch'):
        alerts.append(('ALTITUDE_SPOOFING', 0.85))

    # ------------------------------------------------------------------
    # 6) COMMAND-LEVEL attacks  (from merged cmd_monitor.snapshot())
    #    CommandMonitor already applies the arm/mode grace period, so a
    #    value of >0 here is a genuine post-setup transition.
    # ------------------------------------------------------------------
    if features.get('cmd_arm_changes', 0) > 0:
        alerts.append(('ARM_DISARM_ATTACK', 0.90))
    if features.get('cmd_mode_changes', 0) > 0:
        alerts.append(('MODE_CHANGE_ATTACK', 0.90))
    if features.get('cmd_param_changes', 0) > 0:
        alerts.append(('PARAM_CHANGE_ATTACK', 0.85))
    if features.get('cmd_ack_rate', 0) > 20:
        alerts.append(('COMMAND_SPAM', 0.85))

    # Yaw hijack — a rate over ~170°/s is not a normal flight command.
    if features.get('cmd_yaw_rate_max', 0.0) > 3.0:
        alerts.append(('YAW_HIJACK', 0.85))

    # ------------------------------------------------------------------
    # 7) Comms / jamming
    # ------------------------------------------------------------------
    if features.get('packet_loss_rate', 0.0) > _th('packet_loss_rate'):
        alerts.append(('GPS_JAMMING', 0.80))

    return alerts