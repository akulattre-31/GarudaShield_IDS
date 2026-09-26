"""
M3 EKF Engine
Extended Kalman Filter for GPS spoofing detection via NIS.
"""

import numpy as np
from filterpy.kalman import ExtendedKalmanFilter
from scipy.stats import chi2


class DroneEKF:
    def __init__(self, dt=0.1):
        self.dt = dt
        self.ekf = ExtendedKalmanFilter(dim_x=6, dim_z=3)

        self.ekf.F = np.array([
            [1, 0, 0, dt, 0,  0],
            [0, 1, 0, 0,  dt, 0],
            [0, 0, 1, 0,  0,  dt],
            [0, 0, 0, 1,  0,  0],
            [0, 0, 0, 0,  1,  0],
            [0, 0, 0, 0,  0,  1],
        ])

        self.ekf.H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
        ])

        self.ekf.P *= 10.0
        self.ekf.R *= 50.0
        self.ekf.Q *= 0.1

        self.nis_threshold = chi2.ppf(0.999, df=3)
        print(f"[EKF] NIS threshold: {self.nis_threshold:.2f}")

    def predict(self):
        self.ekf.predict()

    def update_gps(self, gps_position):
        z = np.array(gps_position).reshape(3, 1)
        y = z - self.ekf.H @ self.ekf.x
        S = self.ekf.H @ self.ekf.P @ self.ekf.H.T + self.ekf.R
        nis = float(y.T @ np.linalg.solve(S,y))

        self.ekf.update(z, HJacobian=lambda x: self.ekf.H,
                        Hx=lambda x: self.ekf.H @ x)
        return nis

    def is_spoofed(self, nis):
        return nis > self.nis_threshold
