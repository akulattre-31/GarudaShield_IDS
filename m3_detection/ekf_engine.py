"""
M3 EKF Engine
Extended Kalman Filter for GPS spoofing detection via NIS.

Includes:
  - Warm-up period (skip NIS during initialization)
  - State initialization from first GPS fix
  - Consistent 2D-shape handling for all matrix ops
"""

import numpy as np
from filterpy.kalman import ExtendedKalmanFilter
from scipy.stats import chi2


class DroneEKF:
    def __init__(self, dt=0.1, warmup_updates=20):
        self.dt = dt
        self.warmup_updates = warmup_updates
        self.updates_seen = 0
        self.initialized = False

        self.ekf = ExtendedKalmanFilter(dim_x=6, dim_z=3)

        # State transition matrix (constant velocity model)
        self.ekf.F = np.array([
            [1, 0, 0, dt, 0,  0],
            [0, 1, 0, 0,  dt, 0],
            [0, 0, 1, 0,  0,  dt],
            [0, 0, 0, 1,  0,  0],
            [0, 0, 0, 0,  1,  0],
            [0, 0, 0, 0,  0,  1],
        ], dtype=float)

        # Measurement matrix (GPS measures position only)
        self.ekf.H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
        ], dtype=float)

        # Covariances
        self.ekf.P *= 10.0
        self.ekf.R *= 50.0
        self.ekf.Q *= 0.1

        # NIS threshold (chi-squared, 99.9% confidence, 3 DOF)
        self.nis_threshold = chi2.ppf(0.999, df=3)
        print(f"[EKF] NIS threshold: {self.nis_threshold:.2f}")

    # ------------------------------------------------------------------
    def predict(self):
        """Called on each IMU message. Skip until initialized."""
        if self.initialized:
            self.ekf.predict()

    # ------------------------------------------------------------------
    def update_gps(self, gps_position):
        """
        Called on each GPS message.
        Returns NIS value; 0.0 during warm-up.
        """
        self.updates_seen += 1

        # Make z a proper (3, 1) column vector
        z = np.array(gps_position, dtype=float).reshape(3, 1)

        # ---- First fix: initialize state from GPS, skip NIS ----
        if not self.initialized:
            # Assign to the flat state using the column-slice trick
            self.ekf.x[0:3, 0] = z.flatten()   # position
            self.ekf.x[3:6, 0] = 0.0           # velocity
            self.initialized = True
            print(f"[EKF] State initialized at "
                  f"({z[0,0]:.5f}, {z[1,0]:.5f}, {z[2,0]:.2f})")
            return 0.0

        # ---- Warm-up: update but don't compute NIS ----
        if self.updates_seen < self.warmup_updates:
            self.ekf.update(z,
                            HJacobian=lambda x: self.ekf.H,
                            Hx=lambda x: self.ekf.H @ x)
            return 0.0

        # ---- Normal operation ----
        # Innovation (residual)
        y = z - self.ekf.H @ self.ekf.x            # shape (3, 1)

        # Innovation covariance
        S = self.ekf.H @ self.ekf.P @ self.ekf.H.T + self.ekf.R

        # NIS = yᵀ · S⁻¹ · y  (scalar)
        # Use solve instead of inv for stability and speed
        try:
            nis = float(y.T @ np.linalg.solve(S, y))
        except np.linalg.LinAlgError:
            nis = 0.0

        # Apply the EKF update
        self.ekf.update(z,
                        HJacobian=lambda x: self.ekf.H,
                        Hx=lambda x: self.ekf.H @ x)

        return nis

    # ------------------------------------------------------------------
    def is_spoofed(self, nis):
        """True if NIS exceeds the chi-squared threshold."""
        return nis > self.nis_threshold