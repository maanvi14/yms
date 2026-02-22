# import joblib
# import os
# from datetime import datetime
# import numpy as np


# # =====================================================
# # Load Model (Once at Startup)
# # =====================================================

# MODEL_PATH = os.path.join("app", "ml_models", "best_model.pkl")

# if not os.path.exists(MODEL_PATH):
#     raise FileNotFoundError(
#         f"Model not found at {MODEL_PATH}. Train model first."
#     )

# model = joblib.load(MODEL_PATH)


# # =====================================================
# # 1️⃣ Zone Risk Prediction (UI-READY FORMAT)
# # =====================================================

# def predict_congestion(data: dict):
#     """
#     Predict Zone Operational Risk Score (0–100)
#     Returns Lovable UI-ready congestion card format.
#     """

#     hour = int(data["time_of_day"].split(":")[0])

#     features = [[
#         data["zone_capacity"],
#         data["current_occupancy"],
#         data["overflow_threshold"],
#         data["yard_global_utilization"],
#         data["active_docks"],
#         data["max_concurrent_docks"],
#         data["avg_dock_turnaround_time"],
#         data["dock_unavailability_count"],
#         data["specialized_dock_utilization"],
#         data["pending_moves"],
#         data["failed_moves"],
#         data["blocked_tasks"],
#         data["avg_move_wait_time"],
#         data["avg_dwell_time"],
#         data["oldest_asset_dwell"],
#         data["sla_breaches"],
#         data["sla_deadline_pressure_score"],
#         data["appointment_density"],
#         data["gate_arrival_rate"],
#         data["inbound_eta_pressure"],
#         data["jockey_utilization_ratio"],
#         data["shift_load_factor"],
#         data["live_load_ratio"],
#         data["empty_trailer_ratio"],
#         data["neighbor_zone_pressure_index"],
#         hour
#     ]]

#     predicted = float(model.predict(features)[0])
#     predicted = max(0, min(predicted, 100))

#     # ---------------- Risk Classification ----------------

#     if predicted >= 70:
#         risk = "HIGH"
#     elif predicted >= 40:
#         risk = "MEDIUM"
#     else:
#         risk = "LOW"

#     # ---------------- Forecast Window Logic ----------------

#     if hour < 12:
#         forecast_window = "Next 4h"
#     elif hour < 18:
#         forecast_window = "Next 3h"
#     else:
#         forecast_window = "Next 2h"

#     # ---------------- Intelligent Recommendations ----------------

#     recommendations = []

#     if data["pending_moves"] > 15:
#         recommendations.append("Clear pending trailer moves.")

#     if data["sla_breaches"] > 2:
#         recommendations.append("Prioritize SLA-sensitive trailers.")

#     if data["active_docks"] < data["max_concurrent_docks"] * 0.6:
#         recommendations.append("Activate additional docks.")

#     if data["neighbor_zone_pressure_index"] > 0.7:
#         recommendations.append("Redistribute load to lower-pressure zones.")

#     if data["blocked_tasks"] > 3:
#         recommendations.append("Resolve blocked dock tasks urgently.")

#     if not recommendations:
#         recommendations.append("Zone operating within acceptable limits.")

#     mitigation = " | ".join(recommendations)

#     # ---------------- UI-READY RESPONSE ----------------

#     return {
#         "zone_id": data["zone_id"],
#         "current_utilization": round(data["current_occupancy"] * 100, 2),
#         "predicted_utilization": round(predicted, 2),
#         "risk_level": risk,
#         "forecast_window": forecast_window,
#         "mitigation": mitigation
#     }


# # =====================================================
# # 2️⃣ Global Yard Intelligence Engine
# # =====================================================

# def predict_global_yard_risk(zones):
#     """
#     Network-aware Yard Intelligence Engine
#     """

#     zone_results = []
#     total_capacity = sum(z.zone_capacity for z in zones)
#     total_sla_breaches = 0

#     for zone in zones:
#         result = predict_congestion(zone.dict())

#         zone_results.append({
#             "zone_id": zone.zone_id,
#             "risk_score": result["predicted_utilization"],
#             "neighbor_pressure": zone.neighbor_zone_pressure_index,
#             "current_occupancy": zone.current_occupancy,
#             "overflow_threshold": zone.overflow_threshold
#         })

#         total_sla_breaches += zone.sla_breaches

#     # Capacity Weighted Risk
#     weighted_risk = 0
#     for z, res in zip(zones, zone_results):
#         weight = z.zone_capacity / total_capacity
#         weighted_risk += res["risk_score"] * weight

#     # Spillover Amplification
#     avg_neighbor_pressure = np.mean(
#         [z["neighbor_pressure"] for z in zone_results]
#     )
#     weighted_risk += avg_neighbor_pressure * 10

#     # Cascade Escalation
#     high_zones = [z for z in zone_results if z["risk_score"] >= 70]
#     if len(high_zones) >= 2:
#         weighted_risk += 8

#     # SLA Cluster Override
#     if total_sla_breaches >= 5:
#         weighted_risk += 10

#     # Instability
#     risk_scores = [z["risk_score"] for z in zone_results]
#     instability_index = np.std(risk_scores)
#     weighted_risk += instability_index * 0.5

#     weighted_risk = round(max(0, min(weighted_risk, 100)), 2)

#     # Risk Level Mapping
#     if weighted_risk >= 80:
#         level = "CRITICAL"
#     elif weighted_risk >= 60:
#         level = "HIGH"
#     elif weighted_risk >= 40:
#         level = "MODERATE"
#     else:
#         level = "STABLE"

#     health_index = round(100 - weighted_risk, 2)

#     top_zones = sorted(
#         zone_results,
#         key=lambda x: x["risk_score"],
#         reverse=True
#     )[:3]

#     return {
#         "global_yard_risk_score": weighted_risk,
#         "yard_risk_level": level,
#         "yard_health_index": health_index,
#         "system_instability_index": round(instability_index, 2),
#         "top_risk_zones": [z["zone_id"] for z in top_zones],
#         "rebalancing_recommendation": "Refer to zone-level mitigation strategies.",
#         "timestamp": datetime.utcnow().isoformat()
#     }


# # =====================================================
# # 3️⃣ SLA Risk Engine (Lovable UI Compatible)
# # =====================================================

# def predict_sla_risk(trailers: list):
#     """
#     Trailer-level SLA Breach Prediction
#     Returns Lovable UI-ready SLA cards.
#     """

#     results = []

#     for t in trailers:

#         hours_remaining = t.sla_limit_hours - t.dwell_hours
#         progress_percent = (t.dwell_hours / t.sla_limit_hours) * 100

#         # Risk Level
#         if hours_remaining <= 0:
#             risk = "HIGH"
#             status = f"{abs(round(hours_remaining,1))}h overdue"
#         elif hours_remaining <= 4:
#             risk = "HIGH"
#             status = f"{round(hours_remaining,1)}h to breach"
#         elif hours_remaining <= 8:
#             risk = "MEDIUM"
#             status = f"{round(hours_remaining,1)}h to breach"
#         else:
#             risk = "LOW"
#             status = f"{round(hours_remaining,1)}h to breach"

#         # Contributing Factors
#         factors = []

#         if t.loaded_status == "loaded":
#             factors.append("Loaded drop")

#         if not t.outbound_dock_assigned:
#             factors.append("No outbound dock assigned")

#         if not t.carrier_scheduled:
#             factors.append("No carrier pickup scheduled")

#         # Preventive Action
#         if risk == "HIGH" and not t.outbound_dock_assigned:
#             action = "Schedule outbound dock assignment within 2 hours"
#         elif risk == "HIGH" and not t.carrier_scheduled:
#             action = "Contact carrier for immediate pickup ETA"
#         elif risk == "MEDIUM":
#             action = "Prioritize dock processing"
#         else:
#             action = "Monitor — no immediate action needed"

#         results.append({
#             "trailer_id": t.trailer_id,
#             "risk_level": risk,
#             "status": status,
#             "sla_progress_percent": round(progress_percent, 1),
#             "contributing_factors": factors,
#             "preventive_action": action
#         })

#     return {"trailers": results}

import joblib
import os
from datetime import datetime
import numpy as np


# =====================================================
# Load Model (Once at Startup)
# =====================================================

MODEL_PATH = os.path.join("app", "ml_models", "best_model.pkl")

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(
        f"Model not found at {MODEL_PATH}. Train model first."
    )

print("Loading congestion model...")
model = joblib.load(MODEL_PATH)
print("Model loaded successfully ✅")


# =====================================================
# Helper → Safe Dict Conversion
# =====================================================

def to_dict(obj):
    if hasattr(obj, "model_dump"):  # Pydantic v2
        return obj.model_dump()
    if hasattr(obj, "dict"):        # Pydantic v1
        return obj.dict()
    return obj


# =====================================================
# 1️⃣ Zone Risk Prediction (SAFE NUMERIC INFERENCE)
# =====================================================

def predict_congestion(data: dict):
    """
    Predict Zone Operational Risk Score (0–100)
    Returns Lovable UI-ready congestion card format.
    """

    data = to_dict(data)

    # ---- Parse Hour Safely ----
    hour = int(str(data["time_of_day"])[:2])

    # ---- FORCE NUMERIC ARRAY (CRITICAL FIX) ----
    features = np.array([[
        float(data["zone_capacity"]),
        float(data["current_occupancy"]),
        float(data["overflow_threshold"]),
        float(data["yard_global_utilization"]),
        float(data["active_docks"]),
        float(data["max_concurrent_docks"]),
        float(data["avg_dock_turnaround_time"]),
        float(data["dock_unavailability_count"]),
        float(data["specialized_dock_utilization"]),
        float(data["pending_moves"]),
        float(data["failed_moves"]),
        float(data["blocked_tasks"]),
        float(data["avg_move_wait_time"]),
        float(data["avg_dwell_time"]),
        float(data["oldest_asset_dwell"]),
        float(data["sla_breaches"]),
        float(data["sla_deadline_pressure_score"]),
        float(data["appointment_density"]),
        float(data["gate_arrival_rate"]),
        float(data["inbound_eta_pressure"]),
        float(data["jockey_utilization_ratio"]),
        float(data["shift_load_factor"]),
        float(data["live_load_ratio"]),
        float(data["empty_trailer_ratio"]),
        float(data["neighbor_zone_pressure_index"]),
        float(hour)
    ]], dtype=np.float32)

    # Safety guard (prevents silent freeze forever)
    assert features.dtype != object, "Invalid feature dtype detected!"

    predicted = float(model.predict(features)[0])
    predicted = max(0, min(predicted, 100))

    # ---------------- Risk Classification ----------------
    if predicted >= 70:
        risk = "HIGH"
    elif predicted >= 40:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    # ---------------- Forecast Window ----------------
    if hour < 12:
        forecast_window = "Next 4h"
    elif hour < 18:
        forecast_window = "Next 3h"
    else:
        forecast_window = "Next 2h"

    # ---------------- Recommendations ----------------
    recommendations = []

    if data["pending_moves"] > 15:
        recommendations.append("Clear pending trailer moves.")

    if data["sla_breaches"] > 2:
        recommendations.append("Prioritize SLA-sensitive trailers.")

    if data["active_docks"] < data["max_concurrent_docks"] * 0.6:
        recommendations.append("Activate additional docks.")

    if data["neighbor_zone_pressure_index"] > 0.7:
        recommendations.append("Redistribute load to lower-pressure zones.")

    if data["blocked_tasks"] > 3:
        recommendations.append("Resolve blocked dock tasks urgently.")

    if not recommendations:
        recommendations.append("Zone operating within acceptable limits.")

    mitigation = " | ".join(recommendations)

    return {
        "zone_id": data["zone_id"],
        "current_utilization": round(data["current_occupancy"] * 100, 2),
        "predicted_utilization": round(predicted, 2),
        "risk_level": risk,
        "forecast_window": forecast_window,
        "mitigation": mitigation
    }


# =====================================================
# 2️⃣ Global Yard Intelligence Engine (FIXED LOOP)
# =====================================================

def predict_global_yard_risk(zones):

    zones = [to_dict(z) for z in zones]

    zone_results = []
    total_capacity = sum(z["zone_capacity"] for z in zones)
    total_sla_breaches = 0

    for zone in zones:
        result = predict_congestion(zone)

        zone_results.append({
            "zone_id": zone["zone_id"],
            "risk_score": result["predicted_utilization"],
            "neighbor_pressure": zone["neighbor_zone_pressure_index"],
            "current_occupancy": zone["current_occupancy"],
            "overflow_threshold": zone["overflow_threshold"]
        })

        total_sla_breaches += zone["sla_breaches"]

    # Capacity Weighted Risk
    weighted_risk = sum(
        res["risk_score"] * (z["zone_capacity"] / total_capacity)
        for z, res in zip(zones, zone_results)
    )

    # Spillover Amplification
    avg_neighbor_pressure = np.mean(
        [z["neighbor_pressure"] for z in zone_results]
    )
    weighted_risk += avg_neighbor_pressure * 10

    # Cascade Escalation
    high_zones = [z for z in zone_results if z["risk_score"] >= 70]
    if len(high_zones) >= 2:
        weighted_risk += 8

    # SLA Cluster Override
    if total_sla_breaches >= 5:
        weighted_risk += 10

    # Instability
    risk_scores = [z["risk_score"] for z in zone_results]
    instability_index = float(np.std(risk_scores))
    weighted_risk += instability_index * 0.5

    weighted_risk = round(max(0, min(weighted_risk, 100)), 2)

    # Risk Mapping
    if weighted_risk >= 80:
        level = "CRITICAL"
    elif weighted_risk >= 60:
        level = "HIGH"
    elif weighted_risk >= 40:
        level = "MODERATE"
    else:
        level = "STABLE"

    health_index = round(100 - weighted_risk, 2)

    top_zones = sorted(
        zone_results,
        key=lambda x: x["risk_score"],
        reverse=True
    )[:3]

    return {
        "global_yard_risk_score": weighted_risk,
        "yard_risk_level": level,
        "yard_health_index": health_index,
        "system_instability_index": round(instability_index, 2),
        "top_risk_zones": [z["zone_id"] for z in top_zones],
        "rebalancing_recommendation": "Refer to zone-level mitigation strategies.",
        "timestamp": datetime.utcnow().isoformat()
    }


# =====================================================
# 3️⃣ SLA Risk Engine
# =====================================================

def predict_sla_risk(trailers: list):

    results = []

    for t in trailers:
        t = to_dict(t)

        hours_remaining = t["sla_limit_hours"] - t["dwell_hours"]
        progress_percent = (t["dwell_hours"] / t["sla_limit_hours"]) * 100

        if hours_remaining <= 0:
            risk = "HIGH"
            status = f"{abs(round(hours_remaining,1))}h overdue"
        elif hours_remaining <= 4:
            risk = "HIGH"
        elif hours_remaining <= 8:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        status = f"{round(hours_remaining,1)}h to breach"

        factors = []

        if t["loaded_status"] == "loaded":
            factors.append("Loaded drop")

        if not t["outbound_dock_assigned"]:
            factors.append("No outbound dock assigned")

        if not t["carrier_scheduled"]:
            factors.append("No carrier pickup scheduled")

        if risk == "HIGH" and not t["outbound_dock_assigned"]:
            action = "Schedule outbound dock assignment within 2 hours"
        elif risk == "HIGH" and not t["carrier_scheduled"]:
            action = "Contact carrier for immediate pickup ETA"
        elif risk == "MEDIUM":
            action = "Prioritize dock processing"
        else:
            action = "Monitor — no immediate action needed"

        results.append({
            "trailer_id": t["trailer_id"],
            "risk_level": risk,
            "status": status,
            "sla_progress_percent": round(progress_percent, 1),
            "contributing_factors": factors,
            "preventive_action": action
        })

    return {"trailers": results}