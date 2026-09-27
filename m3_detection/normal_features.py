"""
M3 Feature Extraction
Converts raw telemetry CSV into feature windows.
"""

import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

METERS_PER_DEG_LAT = 111320.0


def latlon_delta_to_meters(lat_delta_deg, lon_delta_deg, ref_lat_deg):
    """
    Convert a (lat, lon) delta in DEGREES to an approximate planar
    displacement in METERS (equirectangular approximation — fine for
    the small deltas seen within one detection window).

    FIX: 'gps_jump' elsewhere in this file is a degree-scale quantity
    (~1e-4). motion_consistency compares GPS-observed displacement
    against a velocity-integrated *meters* displacement
    (speed_m/s * seconds). Comparing degrees to meters made that ratio
    ~1e-5 for ANY moving window, normal or attacked — the feature
    could not distinguish a frozen GPS from a perfectly healthy one.
    This helper produces the meters-scale displacement that the ratio
    actually needs.
    """
    meters_per_deg_lon = METERS_PER_DEG_LAT * np.cos(np.radians(ref_lat_deg))
    dy = lat_delta_deg * METERS_PER_DEG_LAT
    dx = lon_delta_deg * meters_per_deg_lon
    return float(np.sqrt(dx ** 2 + dy ** 2))


def extract_features(csv_path, output_path):
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} rows from {csv_path}")
    print(f"Columns: {list(df.columns)}")

    WINDOW = 10
    STEP = 5

    raw_diffs = df['timestamp_ms'].diff().dropna()
    expected_interval = raw_diffs.median() if len(raw_diffs) > 0 else 250
    print(f"Detected expected interval: {expected_interval} ms")

    MOVING_SPEED_MIN = 0.5

    features = []

    for i in range(0, len(df) - WINDOW, STEP):
        window = df.iloc[i:i + WINDOW].copy()
        feat = {}

        lat = window['latitude']
        lon = window['longitude']
        alt = window['altitude_m']
        vx  = window['vx']
        vy  = window['vy']
        vz  = window['vz']
        t   = window['timestamp_ms']

        # ---------- Navigation ----------
        lat_delta = abs(lat.iloc[-1] - lat.iloc[0])
        lon_delta = abs(lon.iloc[-1] - lon.iloc[0])
        feat['gps_jump'] = np.sqrt(lat_delta ** 2 + lon_delta ** 2)
        # NEW: meters-scale version, used only for motion_consistency below.
        # gps_jump (degrees) is left untouched — GPS_SPOOFING thresholds in
        # rules.py were derived from and are self-consistent with that
        # degree-scale value, so we don't want to disturb that calibration.
        feat['gps_jump_m'] = latlon_delta_to_meters(lat_delta, lon_delta, lat.iloc[0])
        feat['gps_cumulative_drift'] = lat.diff().abs().sum() + lon.diff().abs().sum()
        feat['altitude_drift'] = abs(alt.iloc[-1] - alt.iloc[0])
        feat['altitude_variance'] = alt.var()
        feat['latitude_variance'] = lat.var()
        feat['longitude_variance'] = lon.var()
        dt = t.iloc[-1] - t.iloc[0] + 1e-6
        feat['gps_change_rate'] = feat['gps_jump'] / dt

        # ---------- Control ----------
        speed_3d = np.sqrt(vx ** 2 + vy ** 2 + vz ** 2)
        feat['velocity_magnitude']  = speed_3d.mean()
        feat['velocity_variance']   = vz.var()
        feat['horizontal_speed']    = np.sqrt(vx ** 2 + vy ** 2).mean()
        feat['vertical_speed_mean'] = vz.mean()
        feat['vz_jump']             = abs(vz.iloc[-1] - vz.iloc[0])
        feat['max_velocity_jump']   = vz.diff().abs().max()

        # ---------- Velocity spike ----------
        feat['vx_jump'] = abs(vx.iloc[-1] - vx.iloc[0])
        feat['vy_jump'] = abs(vy.iloc[-1] - vy.iloc[0])
        feat['max_horizontal_velocity_jump'] = max(
            vx.diff().abs().max(),
            vy.diff().abs().max()
        )
        feat['velocity_vector_jump'] = np.sqrt(
            (vx.iloc[-1] - vx.iloc[0]) ** 2 +
            (vy.iloc[-1] - vy.iloc[0]) ** 2 +
            (vz.iloc[-1] - vz.iloc[0]) ** 2
        )

        # ---------- Oscillation ----------
        dvx = vx.diff().dropna()
        dvy = vy.diff().dropna()
        dvz = vz.diff().dropna()
        feat['velocity_oscillation'] = float(
            np.sqrt((dvx ** 2).mean() + (dvy ** 2).mean() + (dvz ** 2).mean())
        )

        sign_flips = 0
        for series in (vx, vy):
            signs = np.sign(series.values)
            sign_flips += int(np.sum(signs[1:] * signs[:-1] < 0))
        feat['direction_change_rate'] = sign_flips / WINDOW

        # ---------- Heading (guarded) ----------
        speed_horiz_series = np.sqrt(vx ** 2 + vy ** 2)
        if speed_horiz_series.mean() > MOVING_SPEED_MIN:
            heading = np.arctan2(vy, vx + 1e-6)
            feat['heading_change'] = abs(heading.iloc[-1] - heading.iloc[0])
        else:
            feat['heading_change'] = 0.0

        # ---------- Communication / Timing ----------
        time_diffs = t.diff().dropna()
        feat['timestamp_variance'] = time_diffs.var() if len(time_diffs) > 1 else 0
        feat['timestamp_mean_interval'] = time_diffs.mean() if len(time_diffs) > 0 else 0
        feat['timestamp_max_gap'] = time_diffs.max() if len(time_diffs) > 0 else 0

        if len(time_diffs) > 0:
            gaps_above = (time_diffs > expected_interval * 1.5).sum()
            feat['packet_loss_rate'] = gaps_above / len(time_diffs)
        else:
            feat['packet_loss_rate'] = 0

        # ---------- Cross-consistency ----------
        feat['gps_velocity_mismatch'] = feat['gps_jump'] / (feat['velocity_magnitude'] + 1e-6)
        feat['position_stability']    = feat['gps_jump'] / (feat['velocity_magnitude'] + 1e-6)

        # --- FIX ---
        # The ratio altitude_drift / |vz_mean| explodes to ~1e3 in hover
        # because vz_mean is ~0. Only compute it when the drone is
        # actually moving vertically; otherwise set it to 0 so hover
        # windows contribute nothing to the derived threshold.
        vz_abs = abs(feat['vertical_speed_mean'])
        if vz_abs > 0.3:
            feat['altitude_velocity_mismatch'] = feat['altitude_drift'] / vz_abs
        else:
            feat['altitude_velocity_mismatch'] = 0.0

        # ---------- Motion Consistency (hover-aware) ----------
        # FIX: compare GPS displacement and velocity-integrated displacement
        # in the SAME units (meters). Previously gps_jump (degrees) was
        # divided by a meters-scale expected_displacement, making this
        # ratio ~1e-5 for essentially every moving window regardless of
        # whether GPS was actually frozen — i.e. it could never
        # discriminate attack from normal flight.
        window_sec = (t.iloc[-1] - t.iloc[0]) / 1000.0 + 1e-6
        vel_mag = feat['velocity_magnitude']
        if vel_mag > 1.0:
            expected_displacement = vel_mag * window_sec
            feat['motion_consistency'] = feat['gps_jump_m'] / (expected_displacement + 1e-6)
        else:
            feat['motion_consistency'] = 1.0

        features.append(feat)

    feature_df = pd.DataFrame(features)
    feature_df = feature_df.fillna(0).replace([np.inf, -np.inf], 0)
    feature_df.to_csv(output_path, index=False)

    print(f"\n✅ Extracted {len(feature_df)} windows × {feature_df.shape[1]} features")
    print(f"✅ Saved to {output_path}")

    constant = [c for c in feature_df.columns if feature_df[c].std() < 1e-9]
    if constant:
        print(f"ℹ️  Constant features (auto-dropped in training): {constant}")

    print("\n=== Feature Statistics ===")
    print(feature_df.describe().T[['mean', 'std', 'min', 'max']].to_string())
    return feature_df


if __name__ == "__main__":
    input_csv  = os.path.join(PROJECT_ROOT, 'data', 'flight_data.csv')
    output_csv = os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv')
    extract_features(input_csv, output_csv)