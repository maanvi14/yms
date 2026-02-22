"""
intent_router.py - Intent Classification & Routing
Determines what the user wants and routes to appropriate handler
"""

import re
import random
import requests
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
# ✅ ADD THIS (do NOT remove anything else)
from app.services.congestion import (
    predict_congestion,
    predict_global_yard_risk,
    predict_sla_risk,
)

class IntentType(Enum):
    """Types of user intents"""
    KNOWLEDGE_QUERY = auto()
    LIVE_STATUS = auto()
    BREACH_CHECK = auto()
    TRAILER_LOOKUP = auto()
    ACTION_REQUEST = auto()
    EXCEPTION_RESOLUTION = auto()
    REPORT_REQUEST = auto()
    HELP_GUIDANCE = auto()
    GREETING = auto()
    CLARIFICATION_NEEDED = auto()
    UNKNOWN = auto()


class ConfidenceLevel(Enum):
    HIGH = 0.9
    MEDIUM = 0.7
    LOW = 0.5


@dataclass
class Intent:
    intent_type: IntentType
    confidence: float
    entities: Dict[str, Any]
    suggested_action: str
    requires_live_data: bool


class IntentRouter:
    """Routes user queries to appropriate handlers"""
    
    def __init__(self):
        self.patterns = {
            IntentType.GREETING: {
                'keywords': ['hi', 'hello', 'hey', 'good morning', 'good afternoon'],
                'regex': [r'^(hi|hello|hey)\b'],
                'priority': 1
            },
            IntentType.LIVE_STATUS: {
                'keywords': ['status', 'current', 'now', 'situation', 'overview', 'summary', 'yard', 'happening', 'going on'],
                'regex': [
                    r'what.*status',
                    r'current.*yard',
                    r'what.*happening',
                    r'yard.*status',
                    r'give me.*overview',
                    r'whatis.*yard',
                    r'what.*the.*current',
                    r'how.*yard',
                    r'yard.*look',
                ],
                'priority': 2
            },
            IntentType.BREACH_CHECK: {
                'keywords': ['breach', 'violation', 'exception', 'overdue', 'exceeded', 'sla', 'risk'],
                'regex': [
                    r'any.*breach',
                    r'sla.*breach',
                    r'exception',
                    r'what.*overdue',
                    r'trailers.*exceed',
                    r'sla.*risk',
                    r'any.*risk',
                ],
                'priority': 2
            },
            IntentType.TRAILER_LOOKUP: {
                'keywords': ['where', 'find', 'locate', 'position', 'trl-', 'trailer'],
                'regex': [
                    r'where.*trl-\d{4}',
                    r'find.*trailer',
                    r'locate.*trl',
                    r'trl-\d{4}.*where',
                    r'where.*container'
                ],
                'priority': 2
            },
            IntentType.ACTION_REQUEST: {
                'keywords': ['check in', 'check out', 'move', 'assign', 'create', 'schedule', 'pending'],
                'regex': [
                    r'check.*in',
                    r'check.*out',
                    r'move.*trailer',
                    r'assign.*dock',
                    r'schedule.*appointment',
                    r'show.*pending',
                    r'pending.*move',
                ],
                'priority': 2
            },
            IntentType.EXCEPTION_RESOLUTION: {
                'keywords': ['resolve', 'fix', 'handle', 'what should i do', 'how to fix'],
                'regex': [
                    r'how.*resolve',
                    r'what.*do.*breach',
                    r'fix.*exception',
                    r'resolve.*sla'
                ],
                'priority': 2
            },
            IntentType.REPORT_REQUEST: {
                'keywords': ['report', 'analytics', 'metrics', 'statistics', 'show me', 'list', 'show'],
                'regex': [
                    r'show.*report',
                    r'generate.*report',
                    r'daily.*summary',
                    r'list.*trailer',
                    r'analytics',
                    r'show.*dock',
                    r'dock.*schedule',
                ],
                'priority': 2
            },
            IntentType.HELP_GUIDANCE: {
                'keywords': ['how to', 'help', 'guide', 'tutorial', 'steps', 'procedure'],
                'regex': [
                    r'how.*use',
                    r'how.*do',
                    r'help.*with',
                    r'guide.*check',
                    r'steps.*'
                ],
                'priority': 2
            },
            IntentType.KNOWLEDGE_QUERY: {
                'keywords': ['what is', 'explain', 'tell me about', 'policy', 'rule'],
                'regex': [
                    r'what.*is',
                    r'explain',
                    r'tell me',
                    r'policy.*',
                    r'rule.*'
                ],
                'priority': 3
            }
        }
        
        self.entity_patterns = {
            'trailer_id': r'TRL-\d{4}',
            'tractor_id': r'TX-\d{4}',
            'zone': r'Zone\s+[A-D]',
            'shipment': r'SHP-\d{6}',
            'time_duration': r'\d+\s*(hour|hr|minute|min|day)',
            'carrier': r'(Schneider|XPO|FedEx|UPS|JB Hunt|Swift)'
        }
    
    def classify(self, query: str) -> Intent:
        """Main classification method"""
        query_lower = query.lower().strip()
        query_normalized = query_lower.replace("'", "").replace("’", "")
        
        scores = {}
        for intent_type, config in self.patterns.items():
            score = self._calculate_score(query_normalized, config)
            scores[intent_type] = score
        
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        if best_score >= ConfidenceLevel.HIGH.value:
            confidence = ConfidenceLevel.HIGH
        elif best_score >= ConfidenceLevel.MEDIUM.value:
            confidence = ConfidenceLevel.MEDIUM
        elif best_score >= ConfidenceLevel.LOW.value:
            confidence = ConfidenceLevel.LOW
        else:
            best_intent = IntentType.UNKNOWN
            confidence = ConfidenceLevel.LOW
        
        entities = self._extract_entities(query_lower)
        
        requires_live = best_intent in [
            IntentType.LIVE_STATUS,
            IntentType.BREACH_CHECK,
            IntentType.TRAILER_LOOKUP
        ]
        
        suggested_action = self._get_suggested_action(best_intent, entities)
        
        return Intent(
            intent_type=best_intent,
            confidence=best_score,
            entities=entities,
            suggested_action=suggested_action,
            requires_live_data=requires_live
        )
    
    def _calculate_score(self, query: str, config: Dict) -> float:
        """Calculate match score for an intent"""
        score = 0.0
        max_score = 0.0
        
        keyword_hits = sum(1 for kw in config['keywords'] if kw in query)
        if config['keywords']:
            score += 0.3 * (keyword_hits / len(config['keywords']))
            max_score += 0.3
        
        regex_hits = sum(1 for pattern in config['regex'] if re.search(pattern, query))
        if config['regex']:
            score += 0.5 * (regex_hits / len(config['regex']))
            max_score += 0.5
        
        exact_phrases = [
            'what is the current yard status',
            'whats the current yard status',
            'any sla breaches',
            'how to check in',
            'where is trl-',
            'show pending moves',
            'pending moves',
            'show dock schedule',
            'dock schedule now',
        ]
        for phrase in exact_phrases:
            if phrase in query:
                score += 0.2
                break
        max_score += 0.2
        
        return score / max_score if max_score > 0 else 0
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract structured data from query"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                clean_matches = [m.upper() if isinstance(m, str) else m[0].upper() for m in matches]
                entities[entity_type] = clean_matches[0] if len(clean_matches) == 1 else clean_matches
        
        numbers = re.findall(r'\d+', query)
        if numbers:
            entities['numbers'] = [int(n) for n in numbers]
        
        time_refs = re.findall(r'(today|yesterday|tomorrow|this week|last week)', query, re.I)
        if time_refs:
            entities['time_reference'] = time_refs[0].lower()
        
        return entities
    
    def _get_suggested_action(self, intent: IntentType, entities: Dict) -> str:
        """Determine what action to take"""
        actions = {
            IntentType.GREETING: "respond_greeting",
            IntentType.LIVE_STATUS: "fetch_yard_status",
            IntentType.BREACH_CHECK: "fetch_breach_list",
            IntentType.TRAILER_LOOKUP: f"fetch_trailer_location:{entities.get('trailer_id', 'unknown')}",
            IntentType.ACTION_REQUEST: "execute_action",
            IntentType.EXCEPTION_RESOLUTION: "fetch_resolution_steps",
            IntentType.REPORT_REQUEST: "generate_report",
            IntentType.HELP_GUIDANCE: "fetch_procedure_guide",
            IntentType.KNOWLEDGE_QUERY: "query_rag_knowledge",
            IntentType.UNKNOWN: "ask_clarification"
        }
        return actions.get(intent, "query_rag_knowledge")
    
    def route(self, query: str, yard_context: Dict = None) -> Dict:
        """Full routing: classify + execute"""
        intent = self.classify(query)
        
        response_plan = {
            "intent": intent.intent_type.name,
            "confidence": round(intent.confidence, 3),
            "entities": intent.entities,
            "action": intent.suggested_action,
            "requires_live_data": intent.requires_live_data,
            "handler": self._get_handler(intent.intent_type),
            "prompt_addition": self._get_context_prompt(intent, yard_context)
        }
        
        return response_plan
    
    def _get_handler(self, intent: IntentType) -> str:
        """Map intent to handler function"""
        handlers = {
            IntentType.GREETING: "handle_greeting",
            IntentType.LIVE_STATUS: "handle_live_status",
            IntentType.BREACH_CHECK: "handle_breach_check",
            IntentType.TRAILER_LOOKUP: "handle_trailer_lookup",
            IntentType.ACTION_REQUEST: "handle_action",
            IntentType.EXCEPTION_RESOLUTION: "handle_resolution",
            IntentType.REPORT_REQUEST: "handle_report",
            IntentType.HELP_GUIDANCE: "handle_help",
            IntentType.KNOWLEDGE_QUERY: "handle_knowledge",
            IntentType.UNKNOWN: "handle_clarification"
        }
        return handlers.get(intent, "handle_knowledge")
    
    def _get_context_prompt(self, intent: IntentType, yard_context: Dict) -> str:
        """Additional context to add to LLM prompt based on intent"""
        
        if intent == IntentType.LIVE_STATUS and yard_context:
            return f"""
Current yard metrics:
- Trailers on-site: {yard_context.get('trailer_count', 'unknown')}
- Dock occupancy: {yard_context.get('dock_occupancy', 'unknown')}/12
- Active moves: {yard_context.get('active_moves', 'unknown')}
- Zone C capacity: {yard_context.get('zones', {}).get('Zone C', 'unknown')}%

Provide a concise summary with these numbers.
"""
        
        elif intent == IntentType.BREACH_CHECK and yard_context:
            breaches = yard_context.get('sla_breaches', [])
            if breaches:
                breach_list = ', '.join([b.get('trailer_id', 'unknown') for b in breaches[:3]])
                return f"""
Active SLA breaches: {len(breaches)}
Most critical: {breach_list}

List each breach with trailer ID, carrier, and violation type.
"""
            else:
                return "No active SLA breaches. Confirm this status."
        
        elif intent == IntentType.TRAILER_LOOKUP:
            return "Provide exact location, zone, and current status of the requested trailer."
        
        return ""


class IntentHandlers:
    """Actual handlers for each intent type"""
    
    def __init__(self, rag_store, db_connection=None, api_base_url="http://localhost:8000"):
        self.rag = rag_store
        self.db = db_connection
        self.api_base_url = api_base_url
    
        def _call_predict_api(self, endpoint: str, data: Any) -> Optional[Dict]:
            """
            Internal prediction call (NO HTTP).
            Prevents FastAPI self-deadlock.
            """

            try:
                print(f"🔥 Internal Prediction Call: {endpoint}")

                # ---- Route internally instead of HTTP ----
                if endpoint == "/predict/congestion":
                    return predict_congestion(data)

                elif endpoint == "/predict/global-yard-risk":
                    return predict_global_yard_risk(data)

                elif endpoint == "/predict/sla-risk":
                    return predict_sla_risk(data)

                else:
                    print(f"Unknown prediction endpoint: {endpoint}")
                    return None

            except Exception as e:
                print(f"🔥 Prediction Exception: {e}")
                return None
    
    def _build_congestion_request(self, yard_context: Dict, zone_id: str = "Zone C") -> Dict:
        """Build CongestionRequest from yard_context"""
        zones = yard_context.get("zones") or {}

        zone_percent = zones.get(zone_id, 50)

        trailer_count = yard_context.get("trailer_count") or 50
        dock_occ = yard_context.get("dock_occupancy") or 6
        active_moves = yard_context.get("active_moves") or 5
        breaches = yard_context.get("sla_breaches") or []
        
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
    
    def handle_greeting(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        greetings = [
            "Hey! I'm YardBuddy 🚛 Ask me anything about the yard — trailer locations, pending moves, dock status, SLA rules, or how to use any feature.",
            "Hello! Ready to help with yard operations. What do you need?",
            "Hi there! I'm your yard assistant. Ask about trailers, docks, or exceptions."
        ]
        return random.choice(greetings)
    
    def handle_live_status(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        # Build base response
        trailers = yard_context.get('trailer_count', 0)
        docks = yard_context.get('dock_occupancy', 0)
        moves = yard_context.get('active_moves', 0)
        zones = yard_context.get('zones', {})
        
        zone_status = ""
        if zones.get('Zone C', 0) > 85:
            zone_status = f" Zone C is nearing capacity at {zones['Zone C']}%,"
        
        response = (
            f"The yard is quite active with {trailers} trailers on-site and {docks} of our 12 "
            f"docks currently occupied. We have {moves} active moves in progress, though{zone_status} "
            f"and you can monitor all these live metrics on the [Dashboard ↗](/dashboard)."
        )
        
        # Get AI prediction - will wait as long as needed
        congestion_request = self._build_congestion_request(yard_context, "Zone C")
        congestion_data = self._call_predict_api("/predict/congestion", congestion_request)
        
        if congestion_data:
            risk = congestion_data.get('risk_level', 'unknown')
            predicted = congestion_data.get('predicted_utilization', 0)
            mitigation = congestion_data.get('mitigation', '')
            
            if risk in ['high', 'critical']:
                response += f" ⚠️ **AI Alert**: Risk level **{risk.upper()}**! Predicted: {predicted:.0f}%. {mitigation}"
            else:
                response += f" 📊 **AI Forecast**: Risk **{risk}**, predicted {predicted:.0f}%."

        return response
    
    def handle_breach_check(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        breaches = yard_context.get('sla_breaches', [])
        
        # Build SLA request - LIST of SLATrailerRequest
        sla_requests = []
        for b in breaches[:5]:
            sla_requests.append({
                "trailer_id": b.get('trailer_id', 'TRL-0000'),
                "dwell_hours": b.get('dwell_time', 0),
                "sla_limit_hours": 12,
                "zone_id": b.get('zone', 'Zone C'),
                "loaded_status": "loaded" if b.get('loaded', True) else "empty",
                "outbound_dock_assigned": b.get('dock_assigned', False),
                "carrier_scheduled": b.get('carrier_scheduled', False)
            })
        
        # If no breaches, send dummy request
        if not sla_requests:
            sla_requests = [{
                "trailer_id": "TRL-DEFAULT",
                "dwell_hours": 0,
                "sla_limit_hours": 12,
                "zone_id": "Zone C",
                "loaded_status": "empty",
                "outbound_dock_assigned": False,
                "carrier_scheduled": False
            }]
        
        # Get AI prediction - will wait as long as needed
        sla_data = self._call_predict_api("/predict/sla-risk", sla_requests)
        
        if not breaches:
            response = "Good news! No active SLA breaches at the moment. All trailers are within dwell time limits."
            if sla_data and sla_data.get('trailers'):
                avg_risk = sum(t.get('sla_progress_percent', 0) for t in sla_data['trailers']) / len(sla_data['trailers'])
                response += f" 📊 **AI Monitor**: Average SLA progress {avg_risk:.0f}%."
            return response
        
        breach_details = []
        for b in breaches[:3]:
            trailer = b.get('trailer_id', 'Unknown')
            carrier = b.get('carrier', 'Unknown carrier')
            reason = b.get('reason', 'SLA violation')
            breach_details.append(f"**{trailer}** ({carrier}) is in breach for {reason}")
        
        details_text = ', and '.join(breach_details)
        
        response = (
            f"Yes, we have {len(breaches)} open exception{'s' if len(breaches) > 1 else ''} right now. "
            f"Most notably, {details_text}. "
            f"You can review all the details and take action on the [Dashboard ↗](/dashboard)."
        )
        
        # Add AI predictions
        if sla_data and sla_data.get('trailers'):
            high_risk = [t for t in sla_data['trailers'] if t.get('risk_level') in ['high', 'critical']]
            if high_risk:
                response += f" 🚨 **AI Alert**: {len(high_risk)} trailers at high risk of breaching!"
        
        return response
    
    def handle_trailer_lookup(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        trailer_id = entities.get('trailer_id', 'Unknown')
        
        trailer_info = {
            'trl-2087': {'zone': 'Zone C', 'position': 'C-14', 'status': 'Loaded, awaiting dispatch', 'dwell': '13.5 hours'},
            'trl-3001': {'zone': 'Zone C', 'position': 'C-22', 'status': 'Reefer, temperature alert', 'dwell': '8 hours'}
        }
        
        info = trailer_info.get(trailer_id.lower(), {
            'zone': 'Unknown', 
            'position': 'Unknown', 
            'status': 'Not found in yard',
            'dwell': 'N/A'
        })
        
        return (
            f"**{trailer_id}** is located in **{info['zone']}** at position **{info['position']}**. "
            f"Status: {info['status']}. "
            f"Dwell time: {info['dwell']}."
        )
    
    def handle_knowledge(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        try:
            from app.ai.rag_store import UserRole as Role
            if user_role and user_role in [r.value for r in Role]:
                role = Role(user_role)
            else:
                role = Role.YARD_SUPERVISOR
            
            result = self.rag.generate(query, role, yard_context)
            return result.get('response', 'I found some information but could not format it properly.')
        except Exception as e:
            print(f"Error in handle_knowledge: {e}")
            return "I'm having trouble accessing the knowledge base right now. Please try again or ask about yard status directly."
    
    def handle_help(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        return self.handle_knowledge(query, entities, yard_context, user_role)
    
    def handle_action(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        return "I'll help you with that action. Please confirm the details on the form, or let me know if you need step-by-step guidance."
    
    def handle_resolution(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        return self.handle_knowledge(query, entities, yard_context, user_role)
    
    def handle_report(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        # Build list of zone requests for global risk
        zone_requests = []
        zones = yard_context.get('zones', {})
        
        for zone_id, capacity in zones.items():
            zone_req = self._build_congestion_request(yard_context, zone_id)
            zone_requests.append(zone_req)
        
        if not zone_requests:
            zone_requests = [self._build_congestion_request(yard_context, "Zone C")]
        
        # Get AI prediction - will wait as long as needed
        global_risk = self._call_predict_api("/predict/global-yard-risk", zone_requests)
        
        base_response = "I can generate that report for you. [View Reports](/reports) or specify date range for custom report."
        
        if global_risk:
            risk_score = global_risk.get('global_yard_risk_score', 0)
            risk_level = global_risk.get('yard_risk_level', 'unknown')
            health = global_risk.get('yard_health_index', 0)
            
            base_response += f" 📊 **Global Yard Health**: {health:.0f}/100 (Risk: {risk_level}, Score: {risk_score:.0f})"
            
            if global_risk.get('top_risk_zones'):
                base_response += f" | Top Risk Zones: {', '.join(global_risk['top_risk_zones'][:3])}"
        
        return base_response
    
    def handle_clarification(self, query: str, entities: Dict, yard_context: Dict, user_role: str = None) -> str:
        return "I'm not sure I understood. Are you asking about: 1) Trailer status, 2) SLA rules, 3) Check-in procedure, or 4) Something else?"

