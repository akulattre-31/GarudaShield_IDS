"""
M3 Runtime Engine — Signed Alerts + Adaptive Thresholds
=========================================================
Detection Layers:
  L0: Source tracking (informational)
  L1: Rate limiter (DoS flood)
  L2: Sequence/sysid validator (injection)
  L3: EKF physics (GPS spoofing)
  L4: Rule-based (statistical thresholds)
  L5: Isolation Forest (unknown anomaly)
  L6: Adaptive thresholds (online recalibration)

Security:
  - HMAC-SHA256 signed alerts (M3 → M5)
  - HMAC-SHA256 verified notifications (M4 → M3)
  - Replay protection via timestamp
  - Encrypted tamper-evident ledger
"""

import os
import sys
import time
import json
import socket
import pickle
import signal
import joblib
import numpy as np
import pandas as pd
from collections import deque
from pymavlink import mavutil

from rules import apply_rules
from ekf_engine import DroneEKF
from cyber_engine import RateLimiter, SequenceValidator
from mitigation import dispatch_failsafe
from forensics import IncidentLedger
from adaptive_thresholds import AdaptiveThresholds
from secure_transport import SecureSender, SecureReceiver

# =====================================================
# CONFIG
# =====================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

MAVLINK_URL = 'udp:0.0.0.0:14551'
ALERT_TO_M5_HOST = '127.0.0.1'          # ← M5's IP if different
ALERT_TO_M5_PORT = 9000
ATTACK_NOTIFY_PORT = 9001
LATENCY_LOG_PATH = os.path.join(PROJECT_ROOT, 'logs', 'latency_log.json')
UNKNOWN_ANOMALIES_PATH = os.path.join(PROJECT_ROOT, 'data', 'unknown_anomalies.pkl')

WINDOW_SEC = 1.0
STEP_SEC = 0.5
ALERT_COOLDOWN_SEC = 3.0
EXPECTED_MSG_INTERVAL_MS = 250

# =====================================================
# STARTUP
# =====================================================
print("[M3] " + "=" * 55)
print("[M3] Drone IDS Runtime Engine — Secure + Adaptive")
print("[M3] " + "=" * 55)

try:
    model = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'ids_model_full.pkl'))
    scaler = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'scaler_full.pkl'))
    feature_names = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'feature_names.pkl'))
    print(f"[M3] Model loaded. Expects {len(feature_names)} features.")
except Exception as e:
    print(f"[M3] ❌ Model load failed: {e}")
    sys.exit(1)

print("[M3] Initializing engines...")
ekf = DroneEKF(dt=0.1)
rate_limiter = RateLimiter(max_hz=1000, window_sec=1.0)
seq_validator = SequenceValidator(expected_sysid=1)
ledger = IncidentLedger()
adaptive = AdaptiveThresholds(window_size=500, update_every=100)
print("[M3] EKF, RateLimiter, SequenceValidator, Ledger, Adaptive ready")

# Secure transport
secure_sender = SecureSender(ALERT_TO_M5_HOST, ALERT_TO_M5_PORT)
notify_receiver = SecureReceiver('0.0.0.0', ATTACK_NOTIFY_PORT, max_age_sec=30)
print("[M3] Signed alerts → M5, signed notifications ← M4")

# State
last_alert_time = 0
buffer = deque(maxlen=500)
unknown_anomalies = []
attack_markers = {}
latency_records = []
running = True


def handle_shutdown(signum, frame):
    global running
    print("\n[M3] Shutdown signal")
    running = False

signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


# =====================================================
# HELPERS
# =====================================================
def save_unknown_anomalies():
    if not unknown_anomalies:
        return
    try:
        with open(UNKNOWN_ANOMALIES_PATH, 'wb') as f:
            pickle.dump(unknown_anomalies, f)
        print(f"[M3] Saved {len(unknown_anomalies)} unknown anomalies")
    except Exception as e:
        print(f"[M3] Save anomalies failed: {e}")


def save_latency_records():
    if not latency_records:
        return
    try:
        os.makedirs(os.path.dirname(LATENCY_LOG_PATH), exist_ok=True)
        with open(LATENCY_LOG_PATH, 'w') as f:
            json.dump(latency_records, f, indent=2)
        print(f"[M3] Saved {len(latency_records)} latency records")
    except Exception as e:
        print(f"[M3] Save latency failed: {e}")


def check_attack_notifications():
    """Read + VERIFY M4's signed attack notifications."""
    for payload in notify_receiver.poll():
        atype = payload.get('type', 'UNKNOWN')
        attack_markers[atype] = time.time()
        print(f"[M3] 🔔 Verified M4 notification: {atype}")


def compute_latency(attack_type):
    if attack_type in attack_markers:
        start_ts = attack_markers.pop(attack_type)
        return (time.time() - start_ts) * 1000
    return None


def emit_alert(master, attack_type, confidence, source, features=None):
    global last_alert_time
    if time.time() - last_alert_time < ALERT_COOLDOWN_SEC:
        return
    last_alert_time = time.time()

    ledger.log(attack_type, confidence, source, features)

    latency_ms = compute_latency(attack_type)
    if latency_ms is not None:
        latency_records.append({
            'attack_type': attack_type,
            'detected_by': source,
            'latency_ms': round(latency_ms, 2),
            'timestamp': time.time()
        })
        print(f"[M3] ⏱️  Latency: {latency_ms:.1f} ms")

    if attack_type == 'UNKNOWN_ANOMALY' and features:
        unknown_anomalies.append({
            'timestamp': time.time(),
            'confidence': confidence,
            'features': features
        })
        if len(unknown_anomalies) % 5 == 0:
            save_unknown_anomalies()

    alert = {
        'timestamp': time.time(),
        'iso_time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'attack_type': attack_type,
        'confidence': round(confidence, 3),
        'source': source,
        'latency_ms': latency_ms,
    }

    # SIGNED send to M5
    try:
        secure_sender.send(alert)
    except Exception as e:
        print(f"[M3] Alert send failed: {e}")

    print(f"[M3] 🚨 {attack_type} (conf={confidence:.2f}, src={source})")

    try:
        dispatch_failsafe(master, attack_type, confidence)
    except Exception as e:
        print(f"[M3] Failsafe error: {e}")


def detect_flight_phase(vx_series, vy_series, vz_series, alt_series):
    """Classify flight phase using data-derived thresholds."""
    speed = np.sqrt(vx_series ** 2 + vy_series ** 2 + vz_series ** 2).mean()
    vz_mean = vz_series.mean()

    hover_max = adaptive.get('hover_speed_max') or 0.85
    takeoff_min = adaptive.get('takeoff_vz_min') or 0.88
    landing_max = adaptive.get('landing_vz_max') or -0.75
    cruise_min = adaptive.get('cruise_speed_min') or 5.21

    if speed < hover_max:
        return 'hover'
    if vz_mean >= takeoff_min:
        return 'takeoff'
    if vz_mean <= landing_max:
        return 'landing'
    if speed >= cruise_min:
        return 'cruise'
    return 'cruise'


def extract_from_window(messages):
    """Extract features with phase awareness + motion consistency."""
    if len(messages) < 5:
        return None

    lats, lons, alts, vxs, vys, vzs, times = [], [], [], [], [], [], []

    for msg in messages:
        if msg.get_type() == 'GLOBAL_POSITION_INT':
            lats.append(msg.lat / 1e7)
            lons.append(msg.lon / 1e7)
            alts.append(msg.alt / 1000.0)
            vxs.append(msg.vx / 100.0)
            vys.append(msg.vy / 100.0)
            vzs.append(msg.vz / 100.0)
        times.append(time.time() * 1000)

    if len(lats) < 3:
        return None

    lat = pd.Series(lats)
    lon = pd.Series(lons)
    alt = pd.Series(alts)
    vx = pd.Series(vxs)
    vy = pd.Series(vys)
    vz = pd.Series(vzs)
    t = pd.Series(times)

    phase = detect_flight_phase(vx, vy, vz, alt)
    feat = {'_phase': phase}

    # Navigation
    lat_delta = abs(lat.iloc[-1] - lat.iloc[0])
    lon_delta = abs(lon.iloc[-1] - lon.iloc[0])
    feat['gps_jump'] = np.sqrt(lat_delta ** 2 + lon_delta ** 2)
    feat['gps_cumulative_drift'] = lat.diff().abs().sum() + lon.diff().abs().sum()
    feat['altitude_drift'] = abs(alt.iloc[-1] - alt.iloc[0])
    feat['altitude_variance'] = alt.var()
    feat['latitude_variance'] = lat.var()
    feat['longitude_variance'] = lon.var()
    dt = t.iloc[-1] - t.iloc[0] + 1e-6
    feat['gps_change_rate'] = feat['gps_jump'] / dt

    # Control
    speed_3d = np.sqrt(vx ** 2 + vy ** 2 + vz ** 2)
    feat['velocity_magnitude'] = speed_3d.mean()
    feat['velocity_variance'] = vz.var()
    feat['horizontal_speed'] = np.sqrt(vx ** 2 + vy ** 2).mean()
    feat['vertical_speed_mean'] = vz.mean()
    feat['vz_jump'] = abs(vz.iloc[-1] - vz.iloc[0])
    feat['max_velocity_jump'] = vz.diff().abs().max()

    moving_min = adaptive.get('moving_speed_min') or 0.5
    speed_horiz = np.sqrt(vx ** 2 + vy ** 2)
    if speed_horiz.mean() > moving_min:
        heading = np.arctan2(vy, vx + 1e-6)
        feat['heading_change'] = abs(heading.iloc[-1] - heading.iloc[0])
    else:
        feat['heading_change'] = 0.0

    # Communication
    time_diffs = t.diff().dropna()
    feat['timestamp_variance'] = time_diffs.var() if len(time_diffs) > 1 else 0
    feat['timestamp_mean_interval'] = time_diffs.mean() if len(time_diffs) > 0 else 0
    feat['timestamp_max_gap'] = time_diffs.max() if len(time_diffs) > 0 else 0
    if len(time_diffs) > 0:
        feat['packet_loss_rate'] = max(0,
            (time_diffs.max() - EXPECTED_MSG_INTERVAL_MS) / EXPECTED_MSG_INTERVAL_MS)
    else:
        feat['packet_loss_rate'] = 0

    # Cross-consistency
    feat['gps_velocity_mismatch'] = feat['gps_jump'] / (feat['velocity_magnitude'] + 1e-6)
    feat['position_stability'] = feat['gps_jump'] / (feat['velocity_magnitude'] + 1e-6)
    feat['altitude_velocity_mismatch'] = feat['altitude_drift'] / (abs(feat['vertical_speed_mean']) + 1e-6)

    # Motion consistency (GPS freeze)
    window_sec = (t.iloc[-1] - t.iloc[0]) / 1000.0 + 1e-6
    expected_displacement = feat['velocity_magnitude'] * window_sec
    feat['motion_consistency'] = feat['gps_jump'] / (expected_displacement + 1e-6)

    return feat


# =====================================================
# MAIN LOOP
# =====================================================
def main():
    global running

    print(f"[M3] Connecting to MAVLink at {MAVLINK_URL}...")
    try:
        master = mavutil.mavlink_connection(MAVLINK_URL)
        master.wait_heartbeat(timeout=30)
        print(f"[M3] ✅ Connected (sysid={master.target_system}, compid={master.target_component})")
    except Exception as e:
        print(f"[M3] ❌ Connection failed: {e}")
        sys.exit(1)

    print(f"[M3] Alerts (signed) → M5 at {ALERT_TO_M5_HOST}:{ALERT_TO_M5_PORT}")
    print(f"[M3] Verifying M4 notifications on {ATTACK_NOTIFY_PORT}")
    print(f"[M3] Press Ctrl+C to stop\n")

    last_extract = time.time()
    msg_count = 0

    while running:
        try:
            check_attack_notifications()

            msg = master.recv_match(blocking=True, timeout=0.1)
            if msg is None:
                continue

            msg_count += 1
            msg_type = msg.get_type()

            # L1: Rate limiter
            exceeded, rate = rate_limiter.check()
            if exceeded:
                emit_alert(master, 'DOS_FLOOD_ALERT', 0.95, 'rate_limiter',
                           {'rate_hz': rate})

            # L2: Sequence validator
            sysid = msg.get_srcSystem() if hasattr(msg, 'get_srcSystem') else 1
            compid = msg.get_srcComponent() if hasattr(msg, 'get_srcComponent') else 1
            msgid = msg.get_msgId() if hasattr(msg, 'get_msgId') else 0
            seq = getattr(msg, 'seq', 0)
            for a in seq_validator.check(sysid, compid, msgid, seq):
                emit_alert(master, a, 0.90, 'seq_validator')

            # L3: EKF
            if msg_type == 'RAW_IMU':
                ekf.predict()
            elif msg_type == 'GLOBAL_POSITION_INT':
                gps = (msg.lat / 1e7, msg.lon / 1e7, msg.alt / 1000.0)
                nis = ekf.update_gps(gps)
                if ekf.is_spoofed(nis):
                    emit_alert(master, 'GPS_SPOOFING_ALERT', 0.95, 'ekf',
                               {'nis': float(nis)})

            buffer.append((time.time(), msg))
            while buffer and time.time() - buffer[0][0] > WINDOW_SEC * 2:
                buffer.popleft()

            # L4 + L5 + L6
            if time.time() - last_extract >= STEP_SEC and len(buffer) > 10:
                messages = [m for _, m in buffer]
                features = extract_from_window(messages)

                if features:
                    phase = features.pop('_phase', 'unknown')

                    feat_vector = [features.get(f, 0) for f in feature_names]
                    X = pd.DataFrame([feat_vector], columns=feature_names)
                    X_scaled = scaler.transform(X)
                    ml_pred = model.predict(X_scaled)[0]
                    ml_score = model.decision_function(X_scaled)[0]

                    rule_alerts = apply_rules(features)
                    is_attack = bool(rule_alerts) or (ml_pred == -1)

                    if rule_alerts:
                        best = max(rule_alerts, key=lambda x: x[1])
                        emit_alert(master, best[0], best[1], 'rule', features)
                    elif ml_pred == -1:
                        conf = min(1.0, max(0.0, (0.1 - ml_score) / 0.2))
                        emit_alert(master, 'UNKNOWN_ANOMALY', conf, 'ml', features)
                    else:
                        if msg_count % 40 == 0:
                            print(f"[M3] ✅ Normal ({phase}) score={ml_score:.3f} msgs={msg_count}")

                    # Feed adaptive engine (uses only clean windows)
                    adaptive.add_sample(
                        speed_3d=features.get('velocity_magnitude', 0),
                        vz=features.get('vertical_speed_mean', 0),
                        speed_horiz=features.get('horizontal_speed', 0),
                        motion_consistency=features.get('motion_consistency', 1.0),
                        is_attack=is_attack,
                    )

                last_extract = time.time()

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[M3] Loop error: {e}")
            time.sleep(0.1)

    print("\n[M3] Shutting down...")
    save_unknown_anomalies()
    save_latency_records()

    ok, bad = ledger.verify()
    print(f"[M3] Ledger integrity: {'✅ VALID' if ok else '❌ TAMPERED'}")
    print(f"[M3] Messages: {msg_count}, Alerts: {len(ledger.entries)}")

    if latency_records:
        avg = sum(r['latency_ms'] for r in latency_records) / len(latency_records)
        print(f"[M3] Average latency: {avg:.1f} ms")

    print("[M3] Stopped.")


if __name__ == '__main__':
    main()