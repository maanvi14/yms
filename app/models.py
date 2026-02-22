from pydantic import BaseModel, Field
from typing import List


# =====================================================
# 1️⃣ Zone Risk Request
# =====================================================

class CongestionRequest(BaseModel):
    zone_id: str = Field(..., example="Zone C")

    # ----- Capacity & Utilization -----
    zone_capacity: int = Field(..., example=120)
    current_occupancy: float = Field(..., example=0.88)
    overflow_threshold: float = Field(..., example=0.85)
    yard_global_utilization: float = Field(..., example=0.82)

    # ----- Dock & Throughput -----
    active_docks: int = Field(..., example=5)
    max_concurrent_docks: int = Field(..., example=10)
    avg_dock_turnaround_time: float = Field(..., example=90)
    dock_unavailability_count: int = Field(..., example=1)
    specialized_dock_utilization: float = Field(..., example=0.8)

    # ----- Movement Pressure -----
    pending_moves: int = Field(..., example=15)
    failed_moves: int = Field(..., example=2)
    blocked_tasks: int = Field(..., example=3)
    avg_move_wait_time: float = Field(..., example=25)

    # ----- SLA & Aging -----
    avg_dwell_time: float = Field(..., example=12)
    oldest_asset_dwell: float = Field(..., example=30)
    sla_breaches: int = Field(..., example=2)
    sla_deadline_pressure_score: float = Field(..., example=0.7)

    # ----- Traffic & Flow -----
    appointment_density: float = Field(..., example=0.9)
    gate_arrival_rate: float = Field(..., example=12)
    inbound_eta_pressure: float = Field(..., example=0.8)

    # ----- Human Factor -----
    jockey_utilization_ratio: float = Field(..., example=1.1)
    shift_load_factor: float = Field(..., example=1.0)

    # ----- Load Mix -----
    live_load_ratio: float = Field(..., example=0.6)
    empty_trailer_ratio: float = Field(..., example=0.3)

    # ----- Network Effect -----
    neighbor_zone_pressure_index: float = Field(..., example=0.5)

    # ----- Time -----
    time_of_day: str = Field(..., example="18:00")


# =====================================================
# 2️⃣ Zone Risk Response (Lovable UI Ready)
# =====================================================

class CongestionResponse(BaseModel):
    zone_id: str
    current_utilization: float
    predicted_utilization: float
    risk_level: str
    forecast_window: str
    mitigation: str


# =====================================================
# 3️⃣ Global Yard Risk Request
# =====================================================

class GlobalYardRiskRequest(BaseModel):
    zones: List[CongestionRequest]


# =====================================================
# 4️⃣ Global Yard Risk Response
# =====================================================

class GlobalYardRiskResponse(BaseModel):
    global_yard_risk_score: float
    yard_risk_level: str
    yard_health_index: float
    system_instability_index: float
    top_risk_zones: List[str]
    rebalancing_recommendation: str
    timestamp: str


# =====================================================
# 5️⃣ SLA Risk Request (Trailer-Level)
# =====================================================

class SLATrailerRequest(BaseModel):
    trailer_id: str
    dwell_hours: float
    sla_limit_hours: float
    zone_id: str
    loaded_status: str  # "loaded" or "empty"
    outbound_dock_assigned: bool
    carrier_scheduled: bool


# =====================================================
# 6️⃣ SLA Risk Response 
# =====================================================

class SLATrailerResponse(BaseModel):
    trailer_id: str
    risk_level: str
    status: str
    sla_progress_percent: float
    contributing_factors: List[str]
    preventive_action: str


class SLABatchResponse(BaseModel):
    trailers: List[SLATrailerResponse]