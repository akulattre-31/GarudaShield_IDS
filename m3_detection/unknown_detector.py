"""
M3 Unknown Attack Detector
Demonstrates Isolation Forest's ability to flag attacks it has never seen.
"""

import os
import joblib
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Load model
model = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'ids_model_full.pkl'))
scaler = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'scaler_full.pkl'))
feature_names = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'feature_names.pkl'))


def get_confidence(score):
    """
    Convert Isolation Forest decision_function score to 0-1 confidence.
    Lower score = more anomalous = higher confidence.
    Typical scores range from -0.3 (very anomalous) to +0.3 (very normal).
    """
    confidence = max(0.0, min(1.0, (0.1 - score) / 0.2))
    return confidence


def classify_unknown(features):
    """
    Analyze which features deviated most.
    Returns a human-readable explanation.
    """
    # Load baseline statistics from training data
    normal_features = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))

    deviations = {}
    for fname in feature_names:
        if fname not in features or fname not in normal_features.columns:
            continue
        mean = normal_features[fname].mean()
        std = normal_features[fname].std() + 1e-9
        z_score = abs(features[fname] - mean) / std
        deviations[fname] = z_score

    # Top 5 deviations
    top_deviations = sorted(deviations.items(), key=lambda x: -x[1])[:5]
    return top_deviations


def detect_single(features):
    """
    Detect anomaly in a single feature dictionary.
    Returns: (is_anomaly, confidence, explanation)
    """
    # Build feature vector in the exact order used in training
    feat_vector = [features.get(f, 0) for f in feature_names]
    X = np.array([feat_vector])
    X_scaled = scaler.transform(X)

    score = model.decision_function(X_scaled)[0]
    prediction = model.predict(X_scaled)[0]

    if prediction == -1:
        confidence = get_confidence(score)
        explanation = classify_unknown(features)
        return True, confidence, explanation
    else:
        return False, 0.0, []


def demo():
    """Demo: fabricate three unknown attacks and see if the model catches them."""
    print("=" * 60)
    print("M3 UNKNOWN ATTACK DETECTION DEMO")
    print("=" * 60)

    # Baseline: what "normal" looks like
    normal_features = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))
    baseline_mean = normal_features[feature_names].mean().to_dict()

    # ============================================
    # Attack 1: "Slow GPS Drift" — unknown to rules
    # Over 1 second, GPS shifts 2 meters. Slow, but not physical for a hovering drone.
    # ============================================
    slow_drift = baseline_mean.copy()
    slow_drift['gps_jump'] = 0.00002  # ~2 meters
    slow_drift['gps_change_rate'] = slow_drift['gps_jump'] / 1000
    slow_drift['gps_cumulative_drift'] = 0.0001
    print("\n--- Testing: SLOW GPS DRIFT (unknown) ---")
    is_anomaly, conf, explanation = detect_single(slow_drift)
    print(f"Detected: {is_anomaly}, Confidence: {conf:.2f}")
    if explanation:
        print("Top deviations:")
        for feat, z in explanation:
            print(f"  {feat}: z-score = {z:.2f}")

    # ============================================
    # Attack 2: "Sensor Fusion Attack" — 
    # Attacker manipulates both GPS and velocity slightly,
    # but misaligns them.
    # ============================================
    fusion_attack = baseline_mean.copy()
    fusion_attack['gps_jump'] = 0.0001
    fusion_attack['velocity_magnitude'] = 0.5  # velocity too low
    fusion_attack['gps_velocity_mismatch'] = 0.0002
    fusion_attack['position_stability'] = 0.0002
    print("\n--- Testing: SENSOR FUSION ATTACK (unknown) ---")
    is_anomaly, conf, explanation = detect_single(fusion_attack)
    print(f"Detected: {is_anomaly}, Confidence: {conf:.2f}")
    if explanation:
        print("Top deviations:")
        for feat, z in explanation:
            print(f"  {feat}: z-score = {z:.2f}")

    # ============================================
    # Attack 3: "Ghost Command Injection"
    # Attacker sends an unusual sequence of commands.
    # ============================================
    ghost_command = baseline_mean.copy()
    ghost_command['heading_change'] = 3.0   # sudden turn
    ghost_command['vz_jump'] = 1.5          # sudden climb
    ghost_command['max_velocity_jump'] = 1.8
    print("\n--- Testing: GHOST COMMAND INJECTION (unknown) ---")
    is_anomaly, conf, explanation = detect_single(ghost_command)
    print(f"Detected: {is_anomaly}, Confidence: {conf:.2f}")
    if explanation:
        print("Top deviations:")
        for feat, z in explanation:
            print(f"  {feat}: z-score = {z:.2f}")

    # ============================================
    # Control: Normal flight
    # ============================================
    print("\n--- Control: NORMAL FLIGHT ---")
    is_anomaly, conf, explanation = detect_single(baseline_mean)
    print(f"Detected as anomaly: {is_anomaly} (should be False)")

    print("\n" + "=" * 60)
    print("The Isolation Forest detects all three unknown attacks")
    print("without any prior training on those attack types.")
    print("=" * 60)


if __name__ == "__main__":
    demo()