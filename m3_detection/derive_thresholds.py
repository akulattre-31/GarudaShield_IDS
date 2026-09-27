"""
M3 Threshold Derivation
Computes statistically-defensible thresholds from normal flight data.
Rule: threshold = mean + k * std (k=5 for high confidence)
"""

import os
import json
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

df = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))

TRACKED = [
    'gps_jump',
    'gps_cumulative_drift',
    'gps_change_rate',
    'packet_loss_rate',
    'timestamp_max_gap',
    'timestamp_variance',
    'heading_change',
    'vz_jump',
    'max_velocity_jump',
    'altitude_drift',
    'altitude_velocity_mismatch',
    'motion_consistency',       # ← ADDED
    'vx_jump',                        # ← NEW
    'vy_jump',                        # ← NEW
    'max_horizontal_velocity_jump',   # ← NEW
    'velocity_vector_jump',           # ← NEW
    'velocity_oscillation',
    'direction_change_rate',
]

K = 5.0
# Features where μ+5σ is too aggressive (heavy-tailed distributions)
PERCENTILE_OVERRIDE = {
    'direction_change_rate': 0.99,    # use 99th percentile
    'velocity_oscillation': 0.99,
}
thresholds = {}

print(f"{'Feature':<30} {'Mean':>12} {'Std':>12} {'Threshold (μ+5σ)':>20}")
print("-" * 80)

for feat in TRACKED:
    if feat not in df.columns:
        print(f"{feat:<30}  ⚠️  not in CSV — skipped")
        continue
    mean = df[feat].mean()
    std = df[feat].std()
    thresh = mean + K * std
    thresh = max(thresh, 1e-6)
    if feat in PERCENTILE_OVERRIDE:
        thresh = df[feat].quantile(PERCENTILE_OVERRIDE[feat])
        thresh = max(thresh, 1e-6)
    thresholds[feat] = round(float(thresh), 8)
    print(f"{feat:<30} {mean:>12.6f} {std:>12.6f} {thresh:>20.6f}")

out_path = os.path.join(PROJECT_ROOT, 'models', 'thresholds.json')
with open(out_path, 'w') as f:
    json.dump(thresholds, f, indent=2)

print(f"\n✅ Saved {len(thresholds)} thresholds to {out_path}")
