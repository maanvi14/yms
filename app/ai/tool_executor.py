"""
tool_executor.py - Tool Execution Engine
Executes tools based on router output. Handles ALL zones, not just Zone C.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.services.congestion import (
    predict_congestion,
    predict_global_yard_risk,
    predict_sla_risk,
)
from app.services.yard_state import get_zone_features, ZONES


@dataclass
class ToolOutput:
    """Standardized output from any tool"""
    tool_name: str
    data: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None


class ToolExecutor:
    """
    Executes tools selected by IntentRouter.
    Supports multi-zone operations.
    """
    
    def __init__(self, rag_store):
        self.rag = rag_store
    
    # ============================================================
    # MAIN ENTRY: Execute tool by name
    # ============================================================
    
    def execute(self, tool_name: str, yard_state: Dict, entities: Dict, user_role: str = None) -> ToolOutput:
        """Route to specific tool implementation"""
        
        tool_map = {
            "congestion_prediction": self.run_congestion_prediction,
            "sla_prediction": self.run_sla_prediction,
            "global_risk_prediction": self.run_global_risk_prediction,
            "trailer_lookup": self.run_trailer_lookup,
            "rag_retrieval": self.run_rag_retrieval,
            "clarification_options": self.run_clarification_options,
        }
        
        if tool_name not in tool_map:
            return ToolOutput(
                tool_name=tool_name,
                data={},
                success=False,
                error_message=f"Unknown tool: {tool_name}"
            )
        
        try:
            return tool_map[tool_name](yard_state, entities, user_role)
        except Exception as e:
            print(f"🔥 Tool execution error ({tool_name}): {e}")
            import traceback
            traceback.print_exc()
            return ToolOutput(
                tool_name=tool_name,
                data={},
                success=False,
                error_message=str(e)
            )
    
    # ============================================================
    # TOOL IMPLEMENTATIONS (Multi-Zone Aware)
    # ============================================================
    
    def run_congestion_prediction(self, yard_state: Dict, entities: Dict, user_role: str = None) -> ToolOutput:
        """
        Run congestion prediction for ALL zones or specific zone from entities.
        NOT just Zone C!
        """
        zones_data = yard_state.get("zones", {})
        
        # Check if user asked about specific zone
        target_zone = entities.get("zone")  # e.g., "Zone A"
        
        predictions = {}
        alerts = []
        
        if target_zone and target_zone in zones_data:
            # Predict for specific zone only
            zone_list = [target_zone]
        else:
            # Predict for ALL zones
            zone_list = list(zones_data.keys()) if zones_data else ZONES
        
        for zone_id in zone_list:
            # Build feature vector for this zone
            zone_features = self._build_congestion_request(yard_state, zone_id)
            
            # Call prediction
            result = predict_congestion(zone_features)
            predictions[zone_id] = result
            
            # Check for alerts
            if result and result.get("risk_level") in ["high", "critical"]:
                alerts.append({
                    "zone": zone_id,
                    "risk_level": result["risk_level"],
                    "predicted_utilization": result.get("predicted_utilization", 0),
                    "mitigation": result.get("mitigation", "")
                })
        
        # Determine highest risk zone
        highest_risk_zone = None
        highest_risk_level = "low"
        risk_priority = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        
        for zone_id, pred in predictions.items():
            level = pred.get("risk_level", "low")
            if risk_priority.get(level, 0) > risk_priority.get(highest_risk_level, 0):
                highest_risk_level = level
                highest_risk_zone = zone_id
        
        return ToolOutput(
            tool_name="congestion_prediction",
            data={
                "predictions": predictions,  # All zones
                "zone_count": len(predictions),
                "alerts": alerts,
                "highest_risk_zone": highest_risk_zone,
                "highest_risk_level": highest_risk_level,
                "target_zone": target_zone  # None if all zones
            },
            success=True
        )
    
    def run_sla_prediction(self, yard_state: Dict, entities: Dict, user_role: str = None) -> ToolOutput:
        """Run SLA risk prediction for trailers with breaches"""
        breaches = yard_state.get("sla_breaches", [])
        
        if not breaches:
            return ToolOutput(
                tool_name="sla_prediction",
                data={
                    "breach_count": 0,
                    "trailers": [],
                    "high_risk_count": 0,
                    "message": "No active SLA breaches"
                },
                success=True
            )
        
        # Build SLA requests for all breached trailers
        sla_requests = []
        for b in breaches[:5]:  # Limit to top 5
            sla_requests.append({
                "trailer_id": b.get("trailer_id", "TRL-0000"),
                "dwell_hours": b.get("dwell_time", 0),
                "sla_limit_hours": 12,
                "zone_id": b.get("zone", "Zone C"),
                "loaded_status": "loaded" if b.get("loaded", True) else "empty",
                "outbound_dock_assigned": b.get("dock_assigned", False),
                "carrier_scheduled": b.get("carrier_scheduled", False)
            })
        
        # Get predictions
        sla_data = predict_sla_risk(sla_requests)
        trailers = sla_data.get("trailers", []) if sla_data else []
        
        # Count high risk
        high_risk = [t for t in trailers if t.get("risk_level") in ["high", "critical"]]
        
        return ToolOutput(
            tool_name="sla_prediction",
            data={
                "breach_count": len(breaches),
                "trailers_analyzed": len(trailers),
                "trailers": trailers,
                "high_risk_count": len(high_risk),
                "high_risk_trailers": high_risk
            },
            success=True
        )
    
    def run_global_risk_prediction(self, yard_state: Dict, entities: Dict, user_role: str = None) -> ToolOutput:
        """Run global yard risk prediction across ALL zones"""
        zones = yard_state.get("zones", {})
        
        # Build requests for ALL zones
        zone_requests = []
        for zone_id in zones.keys():
            zone_req = self._build_congestion_request(yard_state, zone_id)
            zone_requests.append(zone_req)
        
        if not zone_requests:
            # Fallback to all zones if yard_state empty
            for zone_id in ZONES:
                zone_req = self._build_congestion_request(yard_state, zone_id)
                zone_requests.append(zone_req)
        
        # Get global prediction
        global_risk = predict_global_yard_risk(zone_requests)
        
        return ToolOutput(
            tool_name="global_risk_prediction",
            data={
                "global_risk": global_risk or {},
                "zones_analyzed": len(zone_requests),
                "yard_health_index": global_risk.get("yard_health_index", 0) if global_risk else 0,
                "risk_level": global_risk.get("yard_risk_level", "unknown") if global_risk else "unknown",
                "top_risk_zones": global_risk.get("top_risk_zones", []) if global_risk else []
            },
            success=True
        )
    
    def run_trailer_lookup(self, yard_state: Dict, entities: Dict, user_role: str = None) -> ToolOutput:
        """Look up specific trailer location"""
        trailer_id = entities.get("trailer_id", "Unknown")
        
        # Mock database - replace with actual DB query
        trailer_db = {
            "TRL-2087": {
                "trailer_id": "TRL-2087",
                "zone": "Zone C",
                "position": "C-14",
                "status": "Loaded, awaiting dispatch",
                "dwell_hours": 13.5,
                "carrier": "Schneider",
                "has_alert": True,
                "alert_reason": "SLA breach - exceeds 12h dwell"
            },
            "TRL-3001": {
                "trailer_id": "TRL-3001",
                "zone": "Zone C",
                "position": "C-22",
                "status": "Reefer, temperature alert",
                "dwell_hours": 8.0,
                "carrier": "XPO",
                "has_alert": True,
                "alert_reason": "Temperature deviation detected"
            },
            "TRL-1001": {
                "trailer_id": "TRL-1001",
                "zone": "Zone A",
                "position": "A-05",
                "status": "Empty, checked in",
                "dwell_hours": 2.5,
                "carrier": "FedEx",
                "has_alert": False
            }
        }
        
        info = trailer_db.get(trailer_id.upper(), {
            "trailer_id": trailer_id,
            "zone": "Unknown",
            "position": "Unknown",
            "status": "Not found in yard",
            "dwell_hours": None,
            "carrier": "Unknown",
            "has_alert": False
        })
        
        return ToolOutput(
            tool_name="trailer_lookup",
            data={
                "trailer": info,
                "found": info["zone"] != "Unknown",
                "yard_zones": list(yard_state.get("zones", {}).keys())
            },
            success=info["zone"] != "Unknown",
            error_message=None if info["zone"] != "Unknown" else f"Trailer {trailer_id} not found"
        )
    
    def run_rag_retrieval(self, yard_state: Dict, entities: Dict, user_role: str = None) -> ToolOutput:
        """Retrieve relevant documents from RAG"""
        try:
            from app.ai.rag_store import UserRole as Role
            
            if user_role and user_role in [r.value for r in Role]:
                role = Role(user_role)
            else:
                role = Role.YARD_SUPERVISOR
            
            # Get query from entities or use a default
            query = entities.get("query", "yard operations")
            
            # Retrieve documents
            contexts = self.rag.retrieve(query, role, top_k=4)
            
            documents = [
                {
                    "title": ctx.doc.title,
                    "content": ctx.snippet,
                    "doc_type": ctx.doc.doc_type.value,
                    "score": round(ctx.score, 3)
                }
                for ctx in contexts
            ]
            
            return ToolOutput(
                tool_name="rag_retrieval",
                data={
                    "documents": documents,
                    "query": query,
                    "role": user_role,
                    "document_count": len(documents)
                },
                success=len(documents) > 0,
                error_message="No relevant documents found" if not documents else None
            )
            
        except Exception as e:
            return ToolOutput(
                tool_name="rag_retrieval",
                data={"documents": []},
                success=False,
                error_message=str(e)
            )
    
    def run_clarification_options(self, yard_state: Dict, entities: Dict, user_role: str = None) -> ToolOutput:
        """Return clarification options when intent unclear"""
        return ToolOutput(
            tool_name="clarification_options",
            data={
                "options": [
                    {"id": 1, "label": "Trailer status", "example": "Where is TRL-2087?"},
                    {"id": 2, "label": "SLA rules", "example": "What are the dwell time limits?"},
                    {"id": 3, "label": "Check-in procedure", "example": "How do I check in a trailer?"},
                    {"id": 4, "label": "Yard overview", "example": "What's the current yard status?"},
                    {"id": 5, "label": "Zone capacity", "example": "Which zones are full?"}
                ],
                "message": "I'm not sure I understood. Please choose an option or rephrase:"
            },
            success=True
        )
    
    # ============================================================
    # HELPERS
    # ============================================================
    
    def _build_congestion_request(self, yard_state: Dict, zone_id: str) -> Dict:
        """Build congestion request for ANY zone (not just Zone C)"""
        zones = yard_state.get("zones", {})
        
        # Get occupancy for this specific zone, or estimate
        zone_percent = zones.get(zone_id, 70)  # Default 70% if unknown
        
        trailer_count = yard_state.get("trailer_count", 50)
        dock_occ = yard_state.get("dock_occupancy", 6)
        active_moves = yard_state.get("active_moves", 5)
        breaches = yard_state.get("sla_breaches", [])
        
        return {
            "zone_id": zone_id,
            "zone_capacity": 120,
            "current_occupancy": float(zone_percent) / 100.0,
            "overflow_threshold": 0.85,
            "yard_global_utilization": float(trailer_count) / 150.0,
            "active_docks": int(dock_occ),
            "max_concurrent_docks": 12,
            "avg_dock_turnaround_time": 90.0,
            "dock_unavailability_count": 0,
            "specialized_dock_utilization": 0.8,
            "pending_moves": int(active_moves),
            "failed_moves": 0,
            "blocked_tasks": 0,
            "avg_move_wait_time": 25.0,
            "avg_dwell_time": 12.0,
            "oldest_asset_dwell": 30.0,
            "sla_breaches": len(breaches),
            "sla_deadline_pressure_score": 0.7,
            "appointment_density": 0.9,
            "gate_arrival_rate": 12.0,
            "inbound_eta_pressure": 0.8,
            "jockey_utilization_ratio": 1.1,
            "shift_load_factor": 1.0,
            "live_load_ratio": 0.6,
            "empty_trailer_ratio": 0.3,
            "neighbor_zone_pressure_index": 0.5,
            "time_of_day": datetime.now().strftime("%H:%M"),
        }