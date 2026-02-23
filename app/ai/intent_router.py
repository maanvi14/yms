"""
intent_router.py - Pure Intent Classification & Tool Selection
NO handlers here - just routes to tools.
NO service imports - completely tool-agnostic.
"""

import re
from enum import Enum, auto
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# ✅ REMOVED: All service imports - router is now tool-agnostic
# Router only decides WHAT, not HOW


class IntentType(Enum):
    """Types of user intents"""
    GREETING = auto()
    LIVE_STATUS = auto()
    BREACH_CHECK = auto()
    TRAILER_LOOKUP = auto()
    ACTION_REQUEST = auto()
    EXCEPTION_RESOLUTION = auto()
    REPORT_REQUEST = auto()
    HELP_GUIDANCE = auto()
    KNOWLEDGE_QUERY = auto()
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
    requires_live_data: bool


@dataclass
class RouteResult:
    """Clean routing result for assistant layer"""
    intent_name: str              # String for logging/debug
    intent_type: IntentType       # Enum for code branching (avoid string compares)
    confidence: float
    entities: Dict[str, Any]
    tools: List[str]              # Tools to execute
    needs_yard_state: bool        # Whether to fetch yard state
    is_greeting: bool             # Fast-path flag
    requires_live_data: bool      # Legacy flag


class IntentRouter:
    """Pure router - only classifies and selects tools. Zero business logic."""
    
    # Tools that require yard state data
    YARD_STATE_TOOLS = {
        "congestion_prediction", 
        "sla_prediction", 
        "global_risk_prediction",
        "trailer_lookup"
    }
    
    def __init__(self):
        self.patterns = {
            IntentType.GREETING: {
                'keywords': ['hi', 'hello', 'hey', 'good morning', 'good afternoon'],
                'regex': [r'^(hi|hello|hey)\b'],
                'priority': 1
            },
            
            IntentType.LIVE_STATUS: {
                'keywords': ['status', 'current', 'now', 'situation', 'overview', 'summary', 'yard', 'happening', 'going on', 'risk', 'highest', 'which zone'],
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
                    r'which.*zone.*risk',  # ✅ ADD THIS
                    r'highest.*risk',      # ✅ ADD THIS
                    r'zone.*highest',      # ✅ ADD THIS
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
        """Classify intent and extract entities"""
        query_lower = query.lower().strip()
        query_normalized = query_lower.replace("'", "").replace("’", "").replace(",", "")
        
        scores = {}
        for intent_type, config in self.patterns.items():
            score = self._calculate_score(query_normalized, config)
            scores[intent_type] = score
        
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        # Debug logging
        print(f"🔍 Query: '{query}' | Best: {best_intent.name} | Score: {best_score:.3f}")
        
        # ✅ FIX: Lower the threshold or handle yard status queries specially
        if best_score < ConfidenceLevel.LOW.value:
            # Check if it's a yard status query before falling back
            yard_status_keywords = ['yard', 'status', 'zones', 'current', 'overview']
            if any(kw in query_lower for kw in yard_status_keywords):
                print(f"⚠️ Low confidence but yard keywords detected → forcing LIVE_STATUS")
                best_intent = IntentType.LIVE_STATUS
                best_score = 0.6  # Force medium confidence
            else:
                print(f"⚠️ Low confidence ({best_score:.2f}) → fallback to RAG")
                best_intent = IntentType.KNOWLEDGE_QUERY
                best_score = 0.5
        
        entities = self._extract_entities(query_lower)
        
        requires_live = best_intent in [
            IntentType.LIVE_STATUS,
            IntentType.BREACH_CHECK,
            IntentType.TRAILER_LOOKUP
        ]
        
        return Intent(
            intent_type=best_intent,
            confidence=best_score,
            entities=entities,
            requires_live_data=requires_live
        )
    
    def _calculate_score(self, query: str, config: Dict) -> float:
        """Calculate match score"""
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
        ]
        for phrase in exact_phrases:
            if phrase in query:
                score += 0.2
                break
        max_score += 0.2
        
        return score / max_score if max_score > 0 else 0
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """Extract structured entities"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                clean = [m.upper() if isinstance(m, str) else m[0].upper() for m in matches]
                entities[entity_type] = clean[0] if len(clean) == 1 else clean
        
        numbers = re.findall(r'\d+', query)
        if numbers:
            entities['numbers'] = [int(n) for n in numbers]
        
        return entities
    
    def route(self, query: str) -> RouteResult:
        """
        Main routing method.
        Returns structured result for assistant layer to execute.
        """
        intent = self.classify(query)
        tools = self._get_tools_for_intent(intent.intent_type)
        
        # ✅ Compute if yard state needed based on tools, not just intent
        needs_yard_state = any(t in self.YARD_STATE_TOOLS for t in tools)
        
        # ✅ Greeting fast-path
        is_greeting = intent.intent_type == IntentType.GREETING
        
        return RouteResult(
            intent_name=intent.intent_type.name,
            intent_type=intent.intent_type,  # ✅ Enum for code branching
            confidence=round(intent.confidence, 3),
            entities=intent.entities,
            tools=tools,
            needs_yard_state=needs_yard_state,
            is_greeting=is_greeting,
            requires_live_data=intent.requires_live_data
        )
    
    def _get_tools_for_intent(self, intent_type: IntentType) -> List[str]:
        """Map intent to tool names with safety logging"""
        tool_map = {
            IntentType.GREETING: [],
            IntentType.LIVE_STATUS: ["congestion_prediction"],
            IntentType.BREACH_CHECK: ["sla_prediction"],
            IntentType.TRAILER_LOOKUP: ["trailer_lookup"],
            IntentType.ACTION_REQUEST: [],
            IntentType.EXCEPTION_RESOLUTION: ["rag_retrieval"],
            IntentType.REPORT_REQUEST: ["global_risk_prediction"],
            IntentType.HELP_GUIDANCE: ["rag_retrieval"],
            IntentType.KNOWLEDGE_QUERY: ["rag_retrieval"],
            IntentType.CLARIFICATION_NEEDED: ["clarification_options"],
            IntentType.UNKNOWN: ["rag_retrieval"],
        }
        
        # ✅ Safety: log fallback to prevent silent bugs
        if intent_type not in tool_map:
            print(f"⚠️ Unknown intent type: {intent_type} → fallback to RAG")
            return ["rag_retrieval"]
        
        return tool_map[intent_type]