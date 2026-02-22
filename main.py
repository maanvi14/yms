import sys
from pathlib import Path

# Add app folder to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.congestion import router as congestion_router
from app.routes.assistant import router as assistant_router


app = FastAPI(
    title="YMS Predictive Intelligence API",
    description="AI-powered congestion and yard risk intelligence engine with YardBuddy Assistant",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(congestion_router)
app.include_router(assistant_router, prefix="/api/ai", tags=["YardBuddy AI"])


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "YMS API",
        "version": "2.0.0",
        "features": ["congestion_prediction", "yardbuddy_ai"]
    }


@app.get("/health/ai")
async def ai_health():
    try:
        from app.ai.assistant import yard_buddy
        return {
            "status": "healthy",
            "rag_initialized": True,
            "llm": "ollama-llama3"
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}