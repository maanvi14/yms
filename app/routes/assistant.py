"""
YardBuddy AI Assistant API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.ai.assistant import yard_buddy


router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    user_role: str = "yard-supervisor"
    session_id: str = "default"
    yard_context: Optional[Dict[str, Any]] = None


@router.post("/chat")
async def chat(request: ChatRequest):
    """Main YardBuddy chat endpoint"""
    try:
        result = yard_buddy.chat(
            message=request.message,
            user_role=request.user_role,
            session_id=request.session_id,
            yard_context=request.yard_context
        )
        
        return {
            "response": result["response"],
            "intent": result.get("intent"),
            "confidence": result.get("confidence"),
            "sources": result.get("sources", []),
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat(),
            "tool_context": result.get("tool_context")  # ✅ Added full zone data
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history"""
    try:
        history = yard_buddy.get_history(session_id)
        return {
            "session_id": session_id,
            "messages": history,
            "count": len(history)
        }
    except Exception as e:
        import traceback

        print("\n🔥🔥 YARDBUDDY CRASH TRACEBACK 🔥🔥")
        traceback.print_exc()
        print("🔥🔥 END TRACEBACK 🔥🔥\n")

        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear chat history"""
    try:
        result = yard_buddy.clear_history(session_id)
        return {
            "session_id": session_id,
            "cleared": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback

        print("\n🔥🔥 YARDBUDDY CRASH TRACEBACK 🔥🔥")
        traceback.print_exc()
        print("🔥🔥 END TRACEBACK 🔥🔥\n")

        raise HTTPException(status_code=500, detail=str(e))