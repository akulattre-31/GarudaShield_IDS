"""
M3 Threshold Derivation — level-flight only
============================================
Computes statistically-defensible thresholds from NORMAL flight data.

Two safeguards against heavy-tailed training data:

  1. LEVEL-FLIGHT FILTER
     Takeoff and landing transients have velocity changes of 5-10 m/s
     and huge altitude/velocity ratios. If we derive one threshold
     across the whole flight, the normal and attack distributions
     overlap and no percentile separates them. We keep only windows
     where the drone was under steady controlled flight.

  2. PERCENTILE OVERRIDE
     Even after filtering, velocity-jump features have heavy tails
     (a few windows with larger maneuvers survive). For those we use
     the 99th percentile of normal flight as the boundary, instead of
     μ+5σ which is dominated by the tail.
"""

import os
import json
import pandas as pd
import numpy as np

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

df = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))

# --- FIX ---
# Restrict to level-flight windows. The exact bounds depend on your data;
# tune by looking at df['horizontal_speed'].describe() and
# df['vertical_speed_mean'].describe().
if 'horizontal_speed' in df.columns:
    before = len(df)
    df = df[
        (df['horizontal_speed'] > 0.3)
        & (df['horizontal_speed'] < 15.0)
        & (df['vertical_speed_mean'].abs() < 1.0)
        & (df['altitude_drift'] < 1.0)
    ].copy()
    print(f"[filter] level-flight only: {before} -> {len(df)} windows")

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
    'vx_jump',
    'vy_jump',
    'max_horizontal_velocity_jump',
    'velocity_vector_jump',
    'velocity_oscillation',
    'direction_change_rate',
    # NOTE: 'motion_consistency' removed — rules.py reads
    # 'motion_consistency_min' from phase_thresholds.json instead,
    # so the entry here was unused.
]

K = 5.0

# --- FIX ---
# Heavy-tailed features where μ+5σ overshoots the physical range of an
# attack. Use the 99th percentile of normal level flight instead.
PERCENTILE_OVERRIDE = {
    'direction_change_rate':        0.99,   # long tail of sign-flip bursts
    'velocity_oscillation':         0.99,   # long tail of gust windows
    'vx_jump':                      0.99,   # long tail from residual maneuvers
    'vy_jump':                      0.99,
    'vz_jump':                      0.99,
    'max_horizontal_velocity_jump': 0.99,
    'velocity_vector_jump':         0.99,
    'altitude_velocity_mismatch':   0.99,   # still heavy-tailed after filtering
    'max_velocity_jump':            0.99,
    'heading_change':               0.99,
}

# --- FIX ---
# Some features are structurally constant on a localhost SITL link
# (e.g. packet_loss_rate = 0 always — no real network jitter/loss).
# mean + 5*std on a zero-variance column collapses to ~0, floored only
# to 1e-6, which then fires GPS_JAMMING on the very first packet that
# is even slightly delayed the moment this runs over a real radio/WiFi
# link. When a tracked feature has ~zero variance in training, fall
# back to a physically-reasonable default instead of trusting a
# statistic computed from no real variation.
DEGENERATE_STD_FLOOR = 1e-9
DEGENERATE_FALLBACK = {
    'packet_loss_rate': 0.15,   # allow up to 15% loss before flagging jamming
}

thresholds = {}

print(f"\n{'Feature':<32} {'Mean':>12} {'Std':>12} {'Threshold':>14} {'Source':>10}")
print("-" * 90)

for feat in TRACKED:
    if feat not in df.columns:
        print(f"{feat:<32}  ⚠️  not in CSV — skipped")
        continue

    mean = df[feat].mean()
    std  = df[feat].std()

    if feat in PERCENTILE_OVERRIDE:
        thresh = df[feat].quantile(PERCENTILE_OVERRIDE[feat])
        source = f"p{int(PERCENTILE_OVERRIDE[feat]*100)}"
    elif std < DEGENERATE_STD_FLOOR and feat in DEGENERATE_FALLBACK:
        thresh = DEGENERATE_FALLBACK[feat]
        source = "fallback(const)"
    else:
        thresh = mean + K * std
        source = "μ+5σ"

    thresh = max(thresh, 1e-6)
    thresholds[feat] = round(float(thresh), 8)
    print(f"{feat:<32} {mean:>12.6f} {std:>12.6f} {thresh:>14.6f} {source:>10}")

out_path = os.path.join(PROJECT_ROOT, 'models', 'thresholds.json')
with open(out_path, 'w') as f:
    json.dump(thresholds, f, indent=2)

print(f"\n✅ Saved {len(thresholds)} thresholds to {out_path}")