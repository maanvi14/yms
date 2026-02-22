import pandas as pd
import numpy as np
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from xgboost import XGBRegressor


# =====================================================
# 1️. Generate Synthetic Operational Dataset (25 Features)
# =====================================================

np.random.seed(42)
rows = 5000

data = pd.DataFrame({

    # ---- Capacity & Utilization ----
    "zone_capacity": np.random.randint(50, 200, rows),
    "current_occupancy": np.random.uniform(0.4, 0.95, rows),
    "overflow_threshold": np.random.uniform(0.8, 0.9, rows),
    "yard_global_utilization": np.random.uniform(0.4, 0.95, rows),

    # ---- Dock & Throughput ----
    "active_docks": np.random.randint(2, 12, rows),
    "max_concurrent_docks": np.random.randint(5, 15, rows),
    "avg_dock_turnaround_time": np.random.uniform(30, 120, rows),
    "dock_unavailability_count": np.random.randint(0, 4, rows),
    "specialized_dock_utilization": np.random.uniform(0.2, 1.0, rows),

    # ---- Movement Pressure ----
    "pending_moves": np.random.randint(0, 30, rows),
    "failed_moves": np.random.randint(0, 8, rows),
    "blocked_tasks": np.random.randint(0, 6, rows),
    "avg_move_wait_time": np.random.uniform(5, 60, rows),

    # ---- SLA & Aging ----
    "avg_dwell_time": np.random.uniform(2, 20, rows),
    "oldest_asset_dwell": np.random.uniform(8, 48, rows),
    "sla_breaches": np.random.randint(0, 6, rows),
    "sla_deadline_pressure_score": np.random.uniform(0, 1, rows),

    # ---- Traffic & Flow ----
    "appointment_density": np.random.uniform(0.2, 1.0, rows),
    "gate_arrival_rate": np.random.uniform(1, 20, rows),
    "inbound_eta_pressure": np.random.uniform(0, 1, rows),

    # ---- Human Factor ----
    "jockey_utilization_ratio": np.random.uniform(0.5, 1.2, rows),
    "shift_load_factor": np.random.uniform(0.5, 1.2, rows),

    # ---- Load Mix ----
    "live_load_ratio": np.random.uniform(0.2, 0.9, rows),
    "empty_trailer_ratio": np.random.uniform(0.1, 0.6, rows),

    # ---- Network Effect ----
    "neighbor_zone_pressure_index": np.random.uniform(0, 1, rows),

    # ---- Time ----
    "hour_of_day": np.random.randint(0, 24, rows)
})


# =====================================================
# 2️⃣ Define Target: Zone Risk Score (0–100)
# =====================================================

risk = (
    data["current_occupancy"] * 30
    + data["pending_moves"] * 1.5
    + data["blocked_tasks"] * 4
    + data["failed_moves"] * 3
    + data["sla_deadline_pressure_score"] * 15
    + data["inbound_eta_pressure"] * 10
    + data["shift_load_factor"] * 10
    + data["neighbor_zone_pressure_index"] * 8
    - (data["active_docks"] / data["max_concurrent_docks"]) * 20
)

# Add controlled noise for realism
noise = np.random.normal(0, 2, rows)
risk = risk + noise

data["zone_risk_score"] = risk.clip(0, 100)


# =====================================================
# 3️⃣ Train/Test Split
# =====================================================

X = data.drop(columns=["zone_risk_score"])
y = data["zone_risk_score"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


# =====================================================
# 4️⃣ Train XGBoost Model
# =====================================================

model = XGBRegressor(
    n_estimators=350,
    max_depth=6,
    learning_rate=0.07,
    subsample=0.9,
    colsample_bytree=0.9,
    random_state=42,
    verbosity=0
)

model.fit(X_train, y_train)


# =====================================================
# 5️⃣ Evaluate Model
# =====================================================

preds = model.predict(X_test)

r2 = r2_score(y_test, preds)
mae = mean_absolute_error(y_test, preds)

print("\n================ Model Performance ================")
print(f"R2 Score: {r2:.4f}")
print(f"MAE: {mae:.4f}")
print("===================================================")


# =====================================================
# 6️⃣ Save Model
# =====================================================

os.makedirs("app/ml_models", exist_ok=True)

model_path = "app/ml_models/best_model.pkl"
joblib.dump(model, model_path)

print(f"\nRisk model saved successfully at: {model_path}")