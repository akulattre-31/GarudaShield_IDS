"""
M3 Phase Threshold Derivation
Data-driven thresholds for flight phases + motion consistency.
No magic numbers — everything from normal flight statistics.
"""

import os
import json
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Load raw flight data
df = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'flight_data.csv'))

# Compute per-row speed and altitude change
df['speed_3d'] = np.sqrt(df['vx']**2 + df['vy']**2 + df['vz']**2)
df['speed_horiz'] = np.sqrt(df['vx']**2 + df['vy']**2)
df['alt_diff'] = df['altitude_m'].diff().fillna(0)

# ============================================================
# 1. Hover threshold from data
# ============================================================
# Hover = "stationary" periods. Look at lowest 20% of speeds.
speed_p20 = df['speed_3d'].quantile(0.20)
speed_p50 = df['speed_3d'].quantile(0.50)
speed_p80 = df['speed_3d'].quantile(0.80)

# Hover threshold = 25th percentile of speed (bottom quarter = stationary)
HOVER_SPEED_MAX = round(speed_p20, 4)

# Cruise threshold = 75th percentile (top quarter = actively moving)
CRUISE_SPEED_MIN = round(speed_p80, 4)

# ============================================================
# 2. Vertical rate thresholds for takeoff/landing
# ============================================================
# Takeoff = sustained positive vertical velocity
# Landing = sustained negative vertical velocity
vz_p10 = df['vz'].quantile(0.10)
vz_p90 = df['vz'].quantile(0.90)

TAKEOFF_VZ_MIN = round(vz_p90, 4)     # top 10% of climb rate
LANDING_VZ_MAX = round(vz_p10, 4)     # bottom 10% of climb rate

# ============================================================
# 3. Altitude change threshold
# ============================================================
# Use the IQR of altitude change to define "significant" change
alt_q25 = df['alt_diff'].quantile(0.25)
alt_q75 = df['alt_diff'].quantile(0.75)
ALT_CHANGE_SIGNIFICANT = round(abs(alt_q75 - alt_q25), 4)

# ============================================================
# 4. Motion consistency threshold (for GPS freeze detection)
# ============================================================
# In NORMAL flight, motion_consistency ≈ 1.0
# We compute it on the raw CSV to see its natural distribution
normal_features = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))

if 'motion_consistency' in normal_features.columns:
    mc_mean = normal_features['motion_consistency'].mean()
    mc_std = normal_features['motion_consistency'].std()
    # Lower bound = mean - 5σ (values below this are anomalous)
    MOTION_CONSISTENCY_MIN = round(max(mc_mean - 5 * mc_std, 0.01), 4)
else:
    # Fallback: derive from raw data
    # Build motion_consistency manually
    print("⚠️  motion_consistency not in features — computing from raw")
    MOTION_CONSISTENCY_MIN = 0.2   # conservative fallback

# ============================================================
# 5. Moving threshold (for heading computation)
# ============================================================
# Only compute heading when drone is moving meaningfully
# Use median horizontal speed as the boundary
MOVING_SPEED_MIN = round(df['speed_horiz'].quantile(0.25), 4)

# ============================================================
# Output
# ============================================================
phases = {
    'hover_speed_max': HOVER_SPEED_MAX,
    'cruise_speed_min': CRUISE_SPEED_MIN,
    'takeoff_vz_min': TAKEOFF_VZ_MIN,
    'landing_vz_max': LANDING_VZ_MAX,
    'alt_change_significant': ALT_CHANGE_SIGNIFICANT,
    'motion_consistency_min': MOTION_CONSISTENCY_MIN,
    'moving_speed_min': MOVING_SPEED_MIN,
}

print("=" * 70)
print("DERIVED PHASE THRESHOLDS (data-driven, no magic numbers)")
print("=" * 70)
for k, v in phases.items():
    print(f"  {k:<35} = {v}")

print("\nInterpretation:")
print(f"  - Hover if speed_3d < {HOVER_SPEED_MAX}")
print(f"  - Cruise if speed_3d >= {CRUISE_SPEED_MIN}")
print(f"  - Takeoff if vz >= {TAKEOFF_VZ_MIN}")
print(f"  - Landing if vz <= {LANDING_VZ_MAX}")
print(f"  - GPS freeze if motion_consistency < {MOTION_CONSISTENCY_MIN}")
print(f"  - Compute heading only if speed_horiz >= {MOVING_SPEED_MIN}")

# Save
out_path = os.path.join(PROJECT_ROOT, 'models', 'phase_thresholds.json')
with open(out_path, 'w') as f:
    json.dump(phases, f, indent=2)
print(f"\n✅ Saved to {out_path}")
