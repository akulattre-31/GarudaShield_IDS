"""
M3 Rule-Based Detection
Loads statistically-derived thresholds from:
  - models/thresholds.json        (attack-specific thresholds)
  - models/phase_thresholds.json  (flight-phase thresholds + motion consistency)

No hardcoded values. Everything derives from normal flight data.
"""

import os
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

ATTACK_THRESHOLD_PATH = os.path.join(PROJECT_ROOT, 'models', 'thresholds.json')
PHASE_THRESHOLD_PATH = os.path.join(PROJECT_ROOT, 'models', 'phase_thresholds.json')

# Load both threshold files once at import
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
    All thresholds come from JSON files — no magic numbers.
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
    if features.get('packet_loss_rate', 0) > get_threshold('packet_loss_rate'):
        alerts.append(('GPS_JAMMING', 0.85))
    if features.get('timestamp_max_gap', 0) > get_threshold('timestamp_max_gap'):
        alerts.append(('JAMMING_DETECTED', 0.80))
    if features.get('timestamp_variance', 0) > get_threshold('timestamp_variance'):
        alerts.append(('JAMMING_DETECTED', 0.75))

    # ==================== GPS FREEZE ====================
    # Velocity says drone is moving, but GPS shows zero displacement
    if (features.get('motion_consistency', 1.0) < get_phase('motion_consistency_min')
            and features.get('velocity_magnitude', 0) > get_phase('moving_speed_min')):
        alerts.append(('GPS_FREEZE_ATTACK', 0.90))

    # ==================== CONTROL HIJACK ====================
    if features.get('heading_change', 0) > get_threshold('heading_change'):
        alerts.append(('CONTROL_HIJACK', 0.85))
    if features.get('vz_jump', 0) > get_threshold('vz_jump'):
        alerts.append(('CONTROL_HIJACK', 0.75))
    if features.get('max_velocity_jump', 0) > get_threshold('max_velocity_jump'):
        alerts.append(('SUDDEN_CONTROL', 0.75))

    # ==================== ALTITUDE SPOOFING ====================
    if features.get('altitude_drift', 0) > get_threshold('altitude_drift'):
        alerts.append(('ALTITUDE_SPOOFING', 0.80))
    if features.get('altitude_velocity_mismatch', 0) > get_threshold('altitude_velocity_mismatch'):
        alerts.append(('ALTITUDE_SPOOFING', 0.75))

    return alerts