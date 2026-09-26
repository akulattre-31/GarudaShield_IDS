"""
M3 Detection Engine — Demo Test
Simulates attacks by manipulating normal features and checks if the model catches them.
"""

import os
import json
import time
import joblib
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Load model
print("=" * 70)
print("M3 DETECTION ENGINE — DEMO TEST")
print("=" * 70)

model = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'ids_model_full.pkl'))
scaler = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'scaler_full.pkl'))
feature_names = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'feature_names.pkl'))

print(f"\nModel loaded. Expects {len(feature_names)} features.\n")

# Load normal features to get baseline
normal_df = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))
baseline = normal_df[feature_names].mean().to_dict()

# Import rules and EKF
import sys
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'm3_detection'))
from rules import apply_rules
from ekf_engine import DroneEKF


def score_features(features):
    """Run ML detection on a feature dict."""
    vector = [features.get(f, 0) for f in feature_names]
    X = np.array([vector])
    X_scaled = scaler.transform(X)
    pred = model.predict(X_scaled)[0]
    score = model.decision_function(X_scaled)[0]
    confidence = min(1.0, max(0.0, (0.1 - score) / 0.2))
    return pred, score, confidence


def test_scenario(name, features):
    """Test one scenario and report all detection layers."""
    print(f"\n{'─' * 70}")
    print(f"SCENARIO: {name}")
    print(f"{'─' * 70}")

    # Layer 1: ML
    pred, score, conf = score_features(features)
    ml_detected = pred == -1
    print(f"  [ML]     {'🚨 DETECTED' if ml_detected else '✅ normal'} (score={score:.4f}, conf={conf:.2f})")

    # Layer 2: Rules
    rule_alerts = apply_rules(features)
    rules_detected = len(rule_alerts) > 0
    if rules_detected:
        best = max(rule_alerts, key=lambda x: x[1])
        print(f"  [Rules]  🚨 DETECTED: {best[0]} (conf={best[1]:.2f})")
    else:
        print(f"  [Rules]  ✅ normal")

    overall = ml_detected or rules_detected
    print(f"  RESULT:  {'✅ DETECTED' if overall else '❌ MISSED'}")
    return overall


# ============================================================
# ATTACK SCENARIOS (synthetic, built from baseline + injection)
# ============================================================

results = {}

# ---- Baseline: pure normal ----
results['Normal Flight'] = test_scenario('Normal Flight', baseline.copy())

# ---- GPS Spoofing: massive position jump ----
gps_spoof = baseline.copy()
gps_spoof['gps_jump'] = 0.001           # 100x normal
gps_spoof['gps_cumulative_drift'] = 0.01
gps_spoof['gps_change_rate'] = 1e-5
gps_spoof['gps_velocity_mismatch'] = 0.0005
gps_spoof['position_stability'] = 0.0005
results['GPS Spoofing'] = test_scenario('GPS Spoofing', gps_spoof)

# ---- GPS Jamming: packet loss + timing gaps ----
gps_jam = baseline.copy()
gps_jam['packet_loss_rate'] = 0.7
gps_jam['timestamp_max_gap'] = 800.0
gps_jam['timestamp_variance'] = 150.0
results['GPS Jamming'] = test_scenario('GPS Jamming', gps_jam)

# ---- Control Hijack: sudden heading change + velocity spike ----
control_hijack = baseline.copy()
control_hijack['heading_change'] = 4.2
control_hijack['vz_jump'] = 3.0
control_hijack['max_velocity_jump'] = 2.5
results['Control Hijack'] = test_scenario('Control Hijack', control_hijack)

# ---- Altitude Spoofing: alt drift without velocity ----
alt_spoof = baseline.copy()
alt_spoof['altitude_drift'] = 8.0
alt_spoof['altitude_velocity_mismatch'] = 50.0
alt_spoof['altitude_variance'] = 5.0
results['Altitude Spoofing'] = test_scenario('Altitude Spoofing', alt_spoof)

# ---- DoS Flood: extreme message rate ----
dos_flood = baseline.copy()
dos_flood['velocity_variance'] = 5.0
dos_flood['max_velocity_jump'] = 8.0
results['DoS Flood (feature view)'] = test_scenario('DoS Flood (feature view)', dos_flood)

# ---- Slow GPS Drift (unknown attack) ----
slow_drift = baseline.copy()
slow_drift['gps_jump'] = 0.00002
slow_drift['gps_cumulative_drift'] = 0.0005
slow_drift['gps_change_rate'] = 2e-8
results['Slow GPS Drift'] = test_scenario('Slow GPS Drift', slow_drift)

# ---- Unknown Anomaly: subtle multi-feature shift ----
unknown = baseline.copy()
unknown['altitude_velocity_mismatch'] = 500.0
unknown['timestamp_variance'] = 80.0
unknown['velocity_variance'] = 0.8
results['Unknown Anomaly'] = test_scenario('Unknown Anomaly', unknown)


# ============================================================
# EKF PHYSICS TEST (GPS spoofing)
# ============================================================
print(f"\n{'─' * 70}")
print("SCENARIO: GPS Spoofing via EKF (physics-based)")
print(f"{'─' * 70}")

ekf = DroneEKF(dt=0.1)
# Feed 10 normal GPS updates to warm up
for i in range(10):
    ekf.predict()
    ekf.update_gps((0.0, 0.0, 100.0))

# Now feed a spoofed GPS 500m away
ekf.predict()
nis = ekf.update_gps((500.0, 0.0, 100.0))
spoofed = ekf.is_spoofed(nis)
print(f"  NIS value: {nis:.2f}  (threshold: {ekf.nis_threshold:.2f})")
print(f"  RESULT:  {'🚨 DETECTED' if spoofed else '❌ MISSED'}")
results['GPS Spoofing (EKF)'] = spoofed


# ============================================================
# SUMMARY TABLE
# ============================================================
print(f"\n{'=' * 70}")
print("DETECTION SUMMARY")
print(f"{'=' * 70}")
print(f"{'Scenario':<30} {'Detected?':<15}")
print(f"{'-' * 45}")

detected_count = 0
for scenario, detected in results.items():
    status = '✅ YES' if detected else '❌ NO'
    print(f"{scenario:<30} {status:<15}")
    if detected and 'Normal' not in scenario:
        detected_count += 1

total_attacks = len([s for s in results if 'Normal' not in s])
print(f"\nAttacks detected: {detected_count}/{total_attacks}")
print(f"Detection rate:   {detected_count / total_attacks * 100:.1f}%")

if 'Normal Flight' in results:
    if results['Normal Flight']:
        print("\n⚠️  WARNING: Normal flight was flagged — model too sensitive")
    else:
        print("\n✅ Normal flight correctly passed")

print(f"\n{'=' * 70}")
print("Test complete.")
print(f"{'=' * 70}")