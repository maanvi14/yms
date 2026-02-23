# app/services/yard_state.py

from datetime import datetime
from random import randint, uniform, choice


ZONES = ["Zone A", "Zone B", "Zone C", "Zone D"]


def _generate_zone_metrics(zone_id: str):
    """Simulate operational telemetry for one zone"""

    occupancy = uniform(0.55, 0.95)

    return {
        "zone_id": zone_id,
        "zone_capacity": 120,
        "current_occupancy": round(occupancy, 2),
        "overflow_threshold": 0.85,

        "yard_global_utilization": round(uniform(0.65, 0.9), 2),

        "active_docks": randint(4, 9),
        "max_concurrent_docks": 12,
        "avg_dock_turnaround_time": randint(70, 120),

        "dock_unavailability_count": randint(0, 2),
        "specialized_dock_utilization": round(uniform(0.6, 0.95), 2),

        "pending_moves": randint(5, 20),
        "failed_moves": randint(0, 3),
        "blocked_tasks": randint(0, 4),
        "avg_move_wait_time": randint(15, 40),

        "avg_dwell_time": randint(8, 18),
        "oldest_asset_dwell": randint(20, 40),

        "sla_breaches": randint(0, 3),
        "sla_deadline_pressure_score": round(uniform(0.4, 0.9), 2),

        "appointment_density": round(uniform(0.6, 0.95), 2),
        "gate_arrival_rate": randint(8, 18),
        "inbound_eta_pressure": round(uniform(0.5, 0.9), 2),

        "jockey_utilization_ratio": round(uniform(0.8, 1.3), 2),
        "shift_load_factor": round(uniform(0.8, 1.2), 2),

        "live_load_ratio": round(uniform(0.4, 0.7), 2),
        "empty_trailer_ratio": round(uniform(0.2, 0.5), 2),

        "neighbor_zone_pressure_index": round(uniform(0.3, 0.7), 2),

        "time_of_day": datetime.now().strftime("%H:%M"),
    }


def get_current_yard_state():
    """
    Master yard snapshot.
    This replaces manual Swagger inputs.
    """

    zone_data = {
        zone: randint(50, 95) for zone in ZONES
    }

    return {
        "trailer_count": randint(40, 90),
        "dock_occupancy": randint(5, 11),
        "active_moves": randint(3, 15),

        "zones": zone_data,

        "sla_breaches": [
            {
                "trailer_id": "TRL-2087",
                "carrier": choice(["Schneider", "XPO", "FedEx"]),
                "dwell_time": round(uniform(12, 16), 1),
                "zone": "Zone C",
                "loaded": True,
                "dock_assigned": False,
                "carrier_scheduled": False,
            }
        ],
    }


def get_zone_features(zone_id: str):
    """
    Returns FULL feature vector required by congestion model.
    Equivalent to Swagger payload.
    """
    return _generate_zone_metrics(zone_id)