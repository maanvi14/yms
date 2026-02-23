"""
assistant.py - Floating LLM Architecture
Orchestrates tools and lets LLM generate final response.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import ollama

from app.ai.intent_router import IntentRouter, IntentType, RouteResult
from app.ai.tool_executor import ToolExecutor, ToolOutput
from app.ai.rag_store import RAGStore, init_knowledge, UserRole
from app.services.yard_state import get_current_yard_state


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: Optional[str] = None
    sources: Optional[List[Dict]] = None
    tool_context: Optional[Dict] = None


@dataclass
class ToolContext:
    """Combined context for LLM final generation"""
    yard_state: Dict[str, Any] = field(default_factory=dict)
    predictions: Dict[str, Any] = field(default_factory=dict)
    rag_documents: List[Dict] = field(default_factory=list)
    trailer_lookup: Optional[Dict] = None
    user_intent: str = ""
    entities: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "yard_state": self.yard_state,
            "predictions": self.predictions,
            "rag_documents": self.rag_documents,
            "trailer_lookup": self.trailer_lookup,
            "user_intent": self.user_intent,
            "entities": self.entities
        }


class LLMResponseGenerator:
    """LLM-based response generator using ToolContext"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv("LLM_MODEL", "llama3")
    
    def generate(
        self, 
        query: str, 
        tool_context: ToolContext, 
        user_role: str
    ) -> Dict[str, Any]:
        """Generate final response using LLM with tool context"""
        
        system_prompt = self._build_system_prompt(user_role, tool_context)
        user_message = self._build_user_message(query, tool_context)
        
        try:
            print(f"🤖 Generating response with {self.model_name}...")
            
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                options={"temperature": 0.4, "num_predict": 400}
            )
            
            answer = response['message']['content']
            
            return {
                "response": answer,
                "model": self.model_name,
                "sources": self._extract_sources(tool_context)
            }
            
        except Exception as e:
            print(f"🔥 LLM Generation Error: {e}")
            return {
                "response": self._fallback_response(tool_context),
                "model": "fallback",
                "sources": []
            }
    
    def _build_system_prompt(self, user_role: str, context: ToolContext) -> str:
        """Build role-specific system prompt"""
        
        personas = {
            "yard-supervisor": "You are YardBuddy, expert yard supervisor assistant. Strategic, data-driven, concise.",
            "jockey": "You are YardBuddy, jockey assistant. Clear steps, safety-focused, action-oriented.",
            "inspector": "You are YardBuddy, inspector assistant. Thorough, rule-based, detail-oriented.",
            "gate-operator": "You are YardBuddy, gate assistant. Process-focused, efficient, checklist-style.",
            "admin": "You are YardBuddy, admin assistant. Comprehensive, analytical, system-wide view."
        }
        
        persona = personas.get(user_role, "You are YardBuddy, yard assistant. Helpful and concise.")
        
        prompt = f"""{persona}

## RESPONSE RULES
- Use ONLY information explicitly present in the PROVIDED DATA.
- If policy details are missing, say "Information not available in knowledge base."
- NEVER invent numbers, limits, or rules.
- Be specific: cite trailer IDs (TRL-XXXX), zones, and metrics
- Keep responses concise (2-4 sentences max)
- Include markdown links like [Dashboard](/dashboard) when relevant
- For SLA breaches: state trailer ID, carrier, and action needed
- If data shows alerts, mention them with appropriate emojis (⚠️ 🚨 📊)
- For multi-zone data, mention the highest risk zone specifically
"""
        
        # Add available data indicators
        prompt += "\n## AVAILABLE DATA\n"
        if context.yard_state:
            prompt += "- Current yard state (all zones)\n"
        if context.predictions.get("congestion"):
            prompt += "- Congestion predictions (multi-zone)\n"
        if context.predictions.get("sla"):
            prompt += "- SLA risk analysis\n"
        if context.predictions.get("global_risk"):
            prompt += "- Global yard health metrics\n"
        if context.rag_documents:
            prompt += "- Knowledge base documents\n"
        if context.trailer_lookup:
            prompt += "- Specific trailer location\n"
        
        prompt += "\nGenerate a natural, helpful response based on this data."
        
        return prompt
    
    def _build_user_message(self, query: str, context: ToolContext) -> str:
        """Build user message with all tool context"""
        
        sections = [f"User Query: {query}\n"]
        
        # Yard State (ALL zones)
        if context.yard_state:
            ys = context.yard_state
            sections.append("## CURRENT YARD STATE")
            sections.append(f"- Total Trailers: {ys.get('trailer_count', 'N/A')}")
            sections.append(f"- Dock Occupancy: {ys.get('dock_occupancy', 'N/A')}/12")
            sections.append(f"- Active Moves: {ys.get('active_moves', 'N/A')}")
            
            zones = ys.get("zones", {})
            if zones:
                sections.append("- Zone Capacities:")
                for zone, cap in sorted(zones.items()):
                    status = "⚠️ HIGH" if cap > 85 else "OK"
                    sections.append(f"  - {zone}: {cap}% {status}")
            sections.append("")
        
        # Predictions
        if context.predictions:
            sections.append("## AI PREDICTIONS")
            
            # Congestion (Multi-zone)
            if "congestion" in context.predictions:
                c = context.predictions["congestion"]
                sections.append("Congestion Analysis (All Zones):")
                
                predictions = c.get("predictions", {})
                for zone, pred in sorted(predictions.items()):
                    risk = pred.get("risk_level", "unknown")
                    util = pred.get("predicted_utilization", 0)
                    alert = "🚨" if risk in ["high", "critical"] else "✅"
                    sections.append(f"  - {zone}: {risk} risk ({util:.0f}%) {alert}")
                
                if c.get("highest_risk_zone"):
                    sections.append(f"Highest Risk: {c['highest_risk_zone']} ({c['highest_risk_level']})")
                sections.append("")
            
            # SLA
            if "sla" in context.predictions:
                s = context.predictions["sla"]
                sections.append(f"SLA Status: {s.get('breach_count', 0)} breaches")
                if s.get("high_risk_count", 0) > 0:
                    sections.append(f"🚨 High Risk Trailers: {s['high_risk_count']}")
                    for t in s.get("high_risk_trailers", [])[:2]:
                        sections.append(f"  - {t.get('trailer_id')}: {t.get('risk_level')}")
                sections.append("")
            
            # Global Risk
            if "global_risk" in context.predictions:
                g = context.predictions["global_risk"]
                gr = g.get("global_risk", {})
                sections.append(f"Global Yard Health: {gr.get('yard_health_index', 'N/A')}/100")
                sections.append(f"Overall Risk: {gr.get('yard_risk_level', 'unknown')}")
                if gr.get("top_risk_zones"):
                    sections.append(f"Top Risk Zones: {', '.join(gr['top_risk_zones'][:3])}")
                sections.append("")
        
        # Trailer Lookup
        if context.trailer_lookup:
            t = context.trailer_lookup
            sections.append("## TRAILER LOOKUP")
            sections.append(f"Trailer: {t.get('trailer_id')}")
            sections.append(f"Location: {t.get('zone')} at {t.get('position')}")
            sections.append(f"Status: {t.get('status')}")
            if t.get("has_alert"):
                sections.append(f"⚠️ ALERT: {t.get('alert_reason')}")
            sections.append("")
        
        # RAG Documents
        if context.rag_documents:
            sections.append("## RELEVANT KNOWLEDGE")
            for i, doc in enumerate(context.rag_documents[:3], 1):
                sections.append(f"[{i}] {doc.get('title')}")
                sections.append(f"    {doc.get('content', '')[:150]}...")
            sections.append("")
        
        sections.append("Generate a concise, natural response based on this data.")
        
        return "\n".join(sections)
    
    def _extract_sources(self, context: ToolContext) -> List[Dict]:
        """Extract source information for citation"""
        sources = []
        
        if context.rag_documents:
            for doc in context.rag_documents[:3]:
                sources.append({
                    "title": doc.get("title"),
                    "type": "rag",
                    "score": doc.get("score")
                })
        
        if context.predictions:
            sources.append({"title": "AI Prediction Engine", "type": "ml"})
        
        return sources
    
    def _fallback_response(self, context: ToolContext) -> str:
        """Template-based fallback if LLM fails"""
        
        if context.trailer_lookup:
            t = context.trailer_lookup
            return f"**{t.get('trailer_id')}** is in **{t.get('zone')}** at **{t.get('position')}**."
        
        if context.predictions.get("congestion"):
            c = context.predictions["congestion"]
            hrz = c.get("highest_risk_zone")
            hrl = c.get("highest_risk_level")
            return f"Yard status: Highest risk in **{hrz}** ({hrl}). [Dashboard](/dashboard)"
        
        if context.predictions.get("sla"):
            s = context.predictions["sla"]
            return f"SLA: **{s.get('breach_count', 0)} breaches**, {s.get('high_risk_count', 0)} high risk."
        
        return "I found the information. Check the [Dashboard](/dashboard) for details."


class YardBuddyAssistant:
    """
    Floating LLM Architecture:
    1. Route intent
    2. Fetch yard state ONCE
    3. Execute tools
    4. Build ToolContext
    5. LLM generates final response
    """

    def __init__(self):
        # Initialize components
        self.rag = RAGStore()
        init_knowledge(self.rag)
        
        self.router = IntentRouter()
        self.tool_executor = ToolExecutor(rag_store=self.rag)
        self.llm_generator = LLMResponseGenerator()
        
        self.sessions: Dict[str, List[ChatMessage]] = {}
        
        print("✅ YardBuddy Assistant initialized (Floating LLM Architecture)")

    def chat(
        self,
        message: str,
        user_role: str,
        session_id: str = "default",
        yard_context: Optional[Dict] = None
    ) -> Dict:
        """
        Floating LLM flow:
        Route → Fetch Yard State → Execute Tools → LLM Generate → Response
        """
        
        # ---------- 1. Route Intent ----------
        route = self.router.route(message)
        
        print(f"🔍 Intent: {route.intent_name} (confidence: {route.confidence})")
        print(f"🔧 Tools: {route.tools}")
        
        # ---------- 2. GREETING FAST-PATH ----------
        if route.is_greeting:
            greeting = "Hey! I'm YardBuddy 🚛 Ask me anything about the yard!"
            self._store_message(session_id, "user", message)
            self._store_message(session_id, "assistant", greeting, intent=route.intent_name)
            return {
                "response": greeting,
                "intent": route.intent_name,
                "confidence": route.confidence,
                "sources": [],
                "session_id": session_id
            }
        
        # ---------- 3. FETCH YARD STATE ONCE ----------
        # ✅ FIXED: Always fetch fresh yard state for LIVE_STATUS to get all zones
        if route.needs_yard_state:
            if route.intent_type == IntentType.LIVE_STATUS:
                # Always get fresh data for live status
                yard_state = get_current_yard_state()
                print(f"📊 Fresh Yard State: {yard_state.get('trailer_count')} trailers, zones: {list(yard_state.get('zones', {}).keys())}")
            elif yard_context and yard_context.get("zones"):
                yard_state = yard_context
                print(f"📊 Using provided yard context: {list(yard_state.get('zones', {}).keys())}")
            else:
                yard_state = get_current_yard_state()
                print(f"📊 Yard State: {yard_state.get('trailer_count')} trailers, zones: {list(yard_state.get('zones', {}).keys())}")
        else:
            yard_state = yard_context or {}
        
        # ---------- 4. EXECUTE TOOLS ----------
        tool_context = ToolContext(
            yard_state=yard_state,
            user_intent=route.intent_name,
            entities=route.entities
        )
        
        for tool_name in route.tools:
            print(f"⚙️ Executing tool: {tool_name}")
            output = self.tool_executor.execute(
                tool_name=tool_name,
                yard_state=yard_state,
                entities=route.entities,
                user_role=user_role
            )
            
            if output.success:
                self._merge_tool_output(tool_context, tool_name, output)
            else:
                print(f"⚠️ Tool failed: {tool_name} - {output.error_message}")
        
        # ---------- 5. LLM GENERATE FINAL RESPONSE ----------
        print(f"🤖 Generating final response...")
        llm_result = self.llm_generator.generate(
            query=message,
            tool_context=tool_context,
            user_role=user_role
        )
        
        # ---------- 6. STORE AND RETURN ----------
        self._store_message(session_id, "user", message)
        self._store_message(
            session_id, 
            "assistant", 
            llm_result["response"],
            intent=route.intent_name,
            sources=llm_result.get("sources"),
            tool_context=tool_context.to_dict()
        )
        
        return {
            "response": llm_result["response"],
            "intent": route.intent_name,
            "confidence": route.confidence,
            "sources": llm_result.get("sources", []),
            "session_id": session_id,
            "tool_context": tool_context.to_dict()  # For debugging
        }
    
    def _merge_tool_output(self, context: ToolContext, tool_name: str, output: ToolOutput):
        """Merge tool output into context"""
        data = output.data
        
        if tool_name == "congestion_prediction":
            context.predictions["congestion"] = data
        
        elif tool_name == "sla_prediction":
            context.predictions["sla"] = data
        
        elif tool_name == "global_risk_prediction":
            context.predictions["global_risk"] = data
        
        elif tool_name == "trailer_lookup":
            if data.get("found"):
                context.trailer_lookup = data.get("trailer")
        
        elif tool_name == "rag_retrieval":
            context.rag_documents = data.get("documents", [])
    
    def _store_message(self, session_id: str, role: str, content: str, 
                       intent: str = None, sources: List = None, tool_context: Dict = None):
        """Store message in session"""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        self.sessions[session_id].append(ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now().isoformat(),
            sources=sources,
            tool_context=tool_context
        ))
    
    def get_history(self, session_id: str = "default") -> List[Dict]:
        messages = self.sessions.get(session_id, [])
        return [
            {
                "role": m.role,
                "content": m.content,
                "sources": m.sources,
                "tool_context": m.tool_context
            }
            for m in messages
        ]
    
    def clear_history(self, session_id: str = "default"):
        self.sessions[session_id] = []
        return {"cleared": True}


# Singleton Instance
yard_buddy = YardBuddyAssistant()
