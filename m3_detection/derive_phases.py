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
speed_p20 = df['speed_3d'].quantile(0.20)
speed_p80 = df['speed_3d'].quantile(0.80)

HOVER_SPEED_MAX = round(max(speed_p20, 0.5), 4)
CRUISE_SPEED_MIN = round(speed_p80, 4)

# ============================================================
# 2. Vertical rate thresholds for takeoff/landing
# ============================================================
vz_p10 = df['vz'].quantile(0.10)
vz_p90 = df['vz'].quantile(0.90)

TAKEOFF_VZ_MIN = round(vz_p90, 4)
LANDING_VZ_MAX = round(vz_p10, 4)

# ============================================================
# 3. Altitude change threshold
# ============================================================
alt_q25 = df['alt_diff'].quantile(0.25)
alt_q75 = df['alt_diff'].quantile(0.75)
ALT_CHANGE_SIGNIFICANT = round(abs(alt_q75 - alt_q25), 4)

# ============================================================
# 4. Motion consistency threshold (for GPS freeze detection)
# ============================================================
# In NORMAL flight, motion_consistency ≈ 1.0 when moving, and forced
# to exactly 1.0 during hover. A real GPS-freeze attack produces a
# ratio near 0.1 (GPS says "not moving" while IMU says "moving fast").
#
# FIX (2nd pass): after fixing the gps_jump-vs-meters unit bug upstream
# in normal_features.py, motion_consistency now sits in a tight,
# physically sensible band around 1.0 (e.g. observed 0.29-1.01 rather
# than the old 0.000005-1.0). That makes the old fixed 0.35 floor risky
# in the OTHER direction: it can end up ABOVE the real observed minimum
# of normal flight (e.g. min=0.285 < floor=0.35), meaning some
# genuinely-normal windows would already read as "below threshold"
# before any attack occurs.
#
# Use the 1st percentile of normal data instead — the same
# percentile-override approach derive_thresholds.py already uses for
# other heavy-tailed features — so the threshold tracks whatever this
# specific dataset's normal tail actually looks like, rather than a
# number picked by hand. A low sanity floor (0.15) is kept only to
# guard against a tiny/degenerate training set, not as the primary bound.
normal_features = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))

if 'motion_consistency' in normal_features.columns:
    mc = normal_features['motion_consistency']
    mc_mean = mc.mean()
    mc_std = mc.std()
    mc_p01 = mc.quantile(0.01)
    MOTION_CONSISTENCY_MIN = round(max(mc_p01, 0.15), 4)
    print(f"  motion_consistency: mean={mc_mean:.4f} std={mc_std:.4f} "
          f"min={mc.min():.4f} p01={mc_p01:.4f} -> threshold={MOTION_CONSISTENCY_MIN}")
else:
    print("⚠️  motion_consistency not in features — computing from raw")
    MOTION_CONSISTENCY_MIN = 0.15

# ============================================================
# 5. Moving threshold (for heading computation)
# ============================================================
MOVING_SPEED_MIN = round(max(df['speed_horiz'].quantile(0.25), 0.5), 4)

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

out_path = os.path.join(PROJECT_ROOT, 'models', 'phase_thresholds.json')
with open(out_path, 'w') as f:
    json.dump(phases, f, indent=2)
print(f"\n✅ Saved to {out_path}")