"""
M3 Training
Trains Isolation Forest ensemble on normal flight features.
"""

import os
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
FEATURES_CSV = os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)


def train():
    print("=" * 60)
    print("M3 DETECTION ENGINE - TRAINING")
    print("=" * 60)

    X = pd.read_csv(FEATURES_CSV)
    print(f"\n[1/6] Loaded {len(X)} windows × {X.shape[1]} features")

    # Drop constant features
    variances = X.var()
    constant_cols = variances[variances < 1e-9].index.tolist()
    if constant_cols:
        print(f"[2/6] Dropping constant: {constant_cols}")
        X = X.drop(columns=constant_cols)
    else:
        print("[2/6] No constant features")
    print(f"      Remaining: {X.shape[1]} features")

    feature_names = X.columns.tolist()

    # Pre-filter outliers
    print(f"[3/6] Pre-filtering outliers")
    pre = IsolationForest(contamination=0.01, random_state=42, n_jobs=-1)
    pre.fit(X)
    inliers = pre.predict(X) == 1
    X_clean = X[inliers].copy()
    print(f"      Removed {len(X) - len(X_clean)} outliers, training on {len(X_clean)}")

    # Scale
    print(f"[4/6] Scaling features")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_clean)

    # Train ensemble
    print(f"[5/6] Training ensemble (4 models)")
    models = []
    for seed in [42, 7, 123, 999]:
        m = IsolationForest(n_estimators=200, contamination=0.02,
                            random_state=seed, n_jobs=-1)
        m.fit(X_scaled)
        models.append(m)
        print(f"      Model seed={seed} trained")

    # Save
    print(f"[6/6] Saving models")
    joblib.dump(models[0], os.path.join(MODELS_DIR, 'ids_model_full.pkl'))
    joblib.dump(scaler, os.path.join(MODELS_DIR, 'scaler_full.pkl'))
    joblib.dump(feature_names, os.path.join(MODELS_DIR, 'feature_names.pkl'))

    # Top-7 lightweight model
    top7 = variances.drop(labels=constant_cols, errors='ignore').sort_values(ascending=False).head(7).index.tolist()
    print(f"\n      Top 7 features: {top7}")

    X_light = X_clean[top7]
    scaler_light = StandardScaler()
    X_light_scaled = scaler_light.fit_transform(X_light)

    model_light = IsolationForest(n_estimators=50, contamination=0.02, random_state=42, n_jobs=-1)
    model_light.fit(X_light_scaled)

    joblib.dump(model_light, os.path.join(MODELS_DIR, 'ids_model_light.pkl'))
    joblib.dump(scaler_light, os.path.join(MODELS_DIR, 'scaler_light.pkl'))
    joblib.dump(top7, os.path.join(MODELS_DIR, 'top7_features.pkl'))

    # Sanity
    preds_full = models[0].predict(X_scaled)
    preds_light = model_light.predict(X_light_scaled)

    print(f"\nFull model:  Normal={(preds_full == 1).sum()}, Anomalies={(preds_full == -1).sum()}")
    print(f"Light model: Normal={(preds_light == 1).sum()}, Anomalies={(preds_light == -1).sum()}")
    print(f"\n✅ Training complete")


if __name__ == "__main__":
    train()
