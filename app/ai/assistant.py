from typing import Dict, List, Optional
from dataclasses import dataclass

from app.ai.intent_router import IntentRouter, IntentHandlers, IntentType
from app.ai.rag_store import RAGStore, init_knowledge, UserRole


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: Optional[str] = None
    sources: Optional[List[Dict]] = None


class YardBuddyAssistant:
    """
    Main YardBuddy Assistant
    (Updated: removes internal API deadlock)
    """

    def __init__(self):
        # ---------------- RAG ----------------
        self.rag = RAGStore()
        init_knowledge(self.rag)

        # ---------------- Intent Router ----------------
        self.router = IntentRouter()

        # ✅ IMPORTANT CHANGE:
        # No internal HTTP calls anymore
        # api_base_url = None forces local execution
        self.handlers = IntentHandlers(
            rag_store=self.rag,
            db_connection=None,
            api_base_url=None   # 🔥 prevents localhost self-calls
        )

        self.sessions: Dict[str, List[ChatMessage]] = {}

    # =====================================================
    # Chat Entry
    # =====================================================

    def chat(
        self,
        message: str,
        user_role: str,
        session_id: str = "default",
        yard_context: Optional[Dict] = None
    ) -> Dict:

        try:
            role = UserRole(user_role)
        except ValueError:
            role = UserRole.YARD_SUPERVISOR

        # ---------- Session ----------
        if session_id not in self.sessions:
            self.sessions[session_id] = []

        self.sessions[session_id].append(
            ChatMessage(role="user", content=message)
        )

        # ---------- Intent Routing ----------
        route_plan = self.router.route(message, yard_context or {})
        intent_type = IntentType[route_plan["intent"]]

        print(f"🔍 Intent: {route_plan['intent']} ({route_plan['confidence']})")

        # ---------- Execute Handler ----------
        handler_name = route_plan["handler"]
        handler = getattr(self.handlers, handler_name)

        response_text = handler(
            message,
            route_plan["entities"],
            yard_context or {},
            user_role
        )

        # ---------- Store Response ----------
        self.sessions[session_id].append(
            ChatMessage(
                role="assistant",
                content=response_text,
                sources=[]
            )
        )

        return {
            "response": response_text,
            "intent": route_plan["intent"],
            "confidence": route_plan["confidence"],
            "sources": [],
            "session_id": session_id,
        }

    # =====================================================
    # History
    # =====================================================

    def get_history(self, session_id: str = "default") -> List[Dict]:
        messages = self.sessions.get(session_id, [])
        return [
            {"role": m.role, "content": m.content, "sources": m.sources}
            for m in messages
        ]

    def clear_history(self, session_id: str = "default"):
        self.sessions[session_id] = []
        return {"cleared": True}


# =====================================================
# Singleton Instance
# =====================================================

yard_buddy = YardBuddyAssistant()