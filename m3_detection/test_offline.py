"""
M3 Offline Test
Validates the trained model on normal features.
"""

import os
import pandas as pd
import joblib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Load model + scaler + feature names
model = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'ids_model_full.pkl'))
scaler = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'scaler_full.pkl'))
feature_names = joblib.load(os.path.join(PROJECT_ROOT, 'models', 'feature_names.pkl'))

print(f"Model expects {len(feature_names)} features")

# Load full features CSV
X_full = pd.read_csv(os.path.join(PROJECT_ROOT, 'data', 'normal_features.csv'))
print(f"CSV has {X_full.shape[1]} features")

# Select only the features the model was trained on, in the correct order
X = X_full[feature_names]
print(f"Selected {X.shape[1]} features for inference")

# Scale and predict
X_scaled = scaler.transform(X)
preds = model.predict(X_scaled)

total = len(preds)
normal = (preds == 1).sum()
anomalies = (preds == -1).sum()
fpr = anomalies / total * 100

print(f"\nTotal windows: {total}")
print(f"Normal: {normal}")
print(f"Anomalies (False Positives): {anomalies}")
print(f"False Positive Rate: {fpr:.2f}%")
print()
if fpr > 10:
    print("⚠️  FPR too high. Lower contamination to 0.01 and retrain.")
elif fpr < 1:
    print("⚠️  FPR too low. Raise contamination to 0.05 and retrain.")
else:
    print("✅ FPR is in acceptable range.")