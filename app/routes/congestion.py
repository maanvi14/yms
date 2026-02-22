# from fastapi import APIRouter
# from typing import List

# from app.models import (
#     CongestionRequest,
#     CongestionResponse,
#     GlobalYardRiskResponse,
#     SLATrailerRequest,
#     SLABatchResponse
# )

# from app.services.congestion import (
#     predict_congestion,
#     predict_global_yard_risk,
#     predict_sla_risk
# )

# router = APIRouter()


# # =====================================================
# # 1️⃣ Zone-Level Risk Prediction
# # =====================================================

# @router.post("/predict/congestion", response_model=CongestionResponse)
# def congestion_forecast(request: CongestionRequest):
#     return predict_congestion(request.dict())


# # =====================================================
# # 2️⃣ Global Yard Risk Prediction (Multi-Zone)
# # =====================================================

# @router.post("/predict/global-yard-risk", response_model=GlobalYardRiskResponse)
# def global_yard_forecast(request: List[CongestionRequest]):
#     return predict_global_yard_risk(request)


# # =====================================================
# # 3️⃣ SLA & Risk Prediction (Trailer-Level)
# # =====================================================

# @router.post("/predict/sla-risk", response_model=SLABatchResponse)
# def sla_risk_forecast(request: List[SLATrailerRequest]):
#     return predict_sla_risk(request)

from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool
from typing import List

from app.models import (
    CongestionRequest,
    CongestionResponse,
    GlobalYardRiskResponse,
    SLATrailerRequest,
    SLABatchResponse
)

from app.services.congestion import (
    predict_congestion,
    predict_global_yard_risk,
    predict_sla_risk
)

router = APIRouter()


# =====================================================
# Helper → Fast Pydantic Conversion (v1 + v2 compatible)
# =====================================================

def to_dict(model):
    # Pydantic v2
    if hasattr(model, "model_dump"):
        return model.model_dump()
    # Pydantic v1
    return model.dict()


# =====================================================
# 1️⃣ Zone-Level Risk Prediction (ASYNC + NON-BLOCKING)
# =====================================================

@router.post("/predict/congestion", response_model=CongestionResponse)
async def congestion_forecast(request: CongestionRequest):

    result = await run_in_threadpool(
        predict_congestion,
        to_dict(request)
    )

    return result


# =====================================================
# 2️⃣ Global Yard Risk Prediction (Multi-Zone)
# =====================================================

@router.post("/predict/global-yard-risk", response_model=GlobalYardRiskResponse)
async def global_yard_forecast(request: List[CongestionRequest]):

    result = await run_in_threadpool(
        predict_global_yard_risk,
        request
    )

    return result


# =====================================================
# 3️⃣ SLA & Risk Prediction (Trailer-Level)
# =====================================================

@router.post("/predict/sla-risk", response_model=SLABatchResponse)
async def sla_risk_forecast(request: List[SLATrailerRequest]):

    result = await run_in_threadpool(
        predict_sla_risk,
        request
    )

    return result