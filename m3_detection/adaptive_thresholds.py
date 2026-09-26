"""
M3 Online Adaptive Thresholds
Continuously updates thresholds from live telemetry.
Only updates when drone is in a confirmed NORMAL state (no attack).

Fix: moving_speed_min now derived from horizontal speed (matches runtime heading check),
not 3D speed.
"""

import os
import json
import numpy as np
from collections import deque

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PHASE_PATH = os.path.join(PROJECT_ROOT, 'models', 'phase_thresholds.json')


class AdaptiveThresholds:
    """
    Maintains a rolling window of normal flight data.
    Recomputes thresholds every N samples.
    Only updates if no attack was detected in the window.
    """

    def __init__(self, window_size=500, update_every=100):
        self.window_size = window_size
        self.update_every = update_every
        self.samples_since_update = 0
        self.recent_speeds = deque(maxlen=window_size)
        self.recent_speed_horiz = deque(maxlen=window_size)   # ← NEW
        self.recent_vz = deque(maxlen=window_size)
        self.recent_motion_consistency = deque(maxlen=window_size)
        self.attack_flag_recent = deque(maxlen=window_size)
        self.current_thresholds = self._load()

    def _load(self):
        if os.path.exists(PHASE_PATH):
            with open(PHASE_PATH) as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(PHASE_PATH, 'w') as f:
            json.dump(self.current_thresholds, f, indent=2)

    def add_sample(self, speed_3d, vz, speed_horiz, motion_consistency, is_attack):
        """Called every window by runtime_engine."""
        self.recent_speeds.append(speed_3d)
        self.recent_speed_horiz.append(speed_horiz)
        self.recent_vz.append(vz)
        self.recent_motion_consistency.append(motion_consistency)
        self.attack_flag_recent.append(1 if is_attack else 0)

        self.samples_since_update += 1
        if self.samples_since_update >= self.update_every:
            self._maybe_update()
            self.samples_since_update = 0

    def _maybe_update(self):
        """Recompute thresholds if the window is clean (no attacks)."""
        if len(self.recent_speeds) < self.window_size:
            return

        attack_ratio = sum(self.attack_flag_recent) / len(self.attack_flag_recent)
        if attack_ratio > 0.05:
            print(f"[Adaptive] Skipping update — {attack_ratio:.1%} recent attacks")
            return

        speeds = np.array(self.recent_speeds)
        speed_horiz = np.array(self.recent_speed_horiz)
        vz = np.array(self.recent_vz)
        mc = np.array(self.recent_motion_consistency)

        new_thresholds = {
            'hover_speed_max': round(float(np.quantile(speeds, 0.20)), 4),
            'cruise_speed_min': round(float(np.quantile(speeds, 0.80)), 4),
            'takeoff_vz_min': round(float(np.quantile(vz, 0.90)), 4),
            'landing_vz_max': round(float(np.quantile(vz, 0.10)), 4),
            'motion_consistency_min': round(max(float(mc.mean() - 5 * mc.std()), 0.05), 4),
            'moving_speed_min': round(float(np.quantile(speed_horiz, 0.25)), 4),  # ← FIXED
        }

        changed = False
        for k, v in new_thresholds.items():
            old = self.current_thresholds.get(k, 0)
            if old == 0 or abs(v - old) / (abs(old) + 1e-9) > 0.10:
                changed = True
                break

        if changed:
            print(f"[Adaptive] 🔄 Thresholds updated from {len(speeds)} recent windows")
            for k in new_thresholds:
                old = self.current_thresholds.get(k, 0)
                new = new_thresholds[k]
                print(f"  {k}: {old} → {new}")
            self.current_thresholds = new_thresholds
            self._save()

    def get(self, key):
        return self.current_thresholds.get(key)