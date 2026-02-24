**Project Overview**
- **Description**: YMS Predictive Intelligence — a FastAPI backend providing congestion prediction, SLA risk analysis, global yard health metrics and an AI assistant (YardBuddy) that uses RAG + a local LLM for knowledge-aware chat.
- **Root run command**: `uvicorn main:app --reload`

**Architecture**
- **API**: [main.py](main.py) — FastAPI app, CORS middleware, and router registration for prediction and AI endpoints.
- **Services**: `app/services` — Prediction engines and yard-state simulation.
- **AI Layer**: `app/ai` — Intent routing, tool execution, LLM orchestration, and RAG store.
- **Routes**: `app/routes` — HTTP endpoints for predictions and chat.
- **ML**: `app/train_congestion_model.py` (training) → model persisted to `app/ml_models/best_model.pkl` and loaded by the service.

**Key Files & Responsibilities**
- **[main.py](main.py)**: App entry point; includes the congestion and assistant routers and exposes `/` and `/health/ai` endpoints.

- **[app/models.py](app/models.py)**: Pydantic request/response schemas used by the prediction endpoints. Important models:
  - `CongestionRequest` / `CongestionResponse` — zone-level inputs and UI-ready outputs.
  - `GlobalYardRiskRequest` / `GlobalYardRiskResponse` — multi-zone payloads and aggregated yard health.
  - `SLATrailerRequest` / `SLATrailerResponse` — trailer-level SLA checks and batch responses.

- **[app/train_congestion_model.py](app/train_congestion_model.py)**: Synthetic-data generator and training script using XGBoost. Generates 25 feature columns, defines a handcrafted risk target, trains an XGBRegressor, evaluates (R2/MAE), and saves the model to `app/ml_models/best_model.pkl`.

- **[app/services/yard_state.py](app/services/yard_state.py)**: Provides simulated yard telemetry
  - `get_current_yard_state()` — returns a snapshot used by the assistant and tools.
  - `get_zone_features(zone_id)` — returns a full feature vector for one zone (used by tool executor to build model input).

- **[app/services/congestion.py](app/services/congestion.py)**: Core prediction services that load the trained ML model at import time and expose three main functions:
  - `predict_congestion(data: dict)` — converts input into numeric features, runs the XGBoost model, clamps the output to [0,100], classifies risk (LOW/MEDIUM/HIGH), selects a forecast window, and returns a UI-ready dictionary containing `zone_id`, `current_utilization`, `predicted_utilization`, `risk_level`, `forecast_window`, and `mitigation` suggestions.
  - `predict_global_yard_risk(zones)` — aggregates zone-level predictions into a capacity-weighted global risk score, applies spillover and cascade heuristics, computes instability and top risk zones, and returns a structured health object.
  - `predict_sla_risk(trailers: list)` — computes trailer-level SLA status, risk levels, contributing factors, and preventive actions; returns a list of SLA cards.

- **[app/routes/congestion.py](app/routes/congestion.py)**: HTTP endpoints exposing the services above. Endpoints are asynchronous and use `run_in_threadpool` to avoid blocking:
  - `POST /predict/congestion` — `CongestionRequest` → `predict_congestion`
  - `POST /predict/global-yard-risk` — list of `CongestionRequest` → `predict_global_yard_risk`
  - `POST /predict/sla-risk` — list of `SLATrailerRequest` → `predict_sla_risk`

- **AI: [app/ai/assistant.py](app/ai/assistant.py)**
  - `YardBuddyAssistant` — high-level orchestrator following a "Floating LLM Architecture":
    1. Uses `IntentRouter` to classify user query and select tools.
    2. Fetches yard state once (if needed) via `get_current_yard_state()`.
    3. Uses `ToolExecutor` to run selected tools and merges outputs into a `ToolContext`.
    4. Uses `LLMResponseGenerator` (wraps Ollama) to generate a final, human-friendly response, passing tool context as part of the system/user prompt.
  - `LLMResponseGenerator` — builds role-specific system prompts, composes data sections (yard state, predictions, trailer lookup, RAG hits), calls `ollama.chat`, and returns response + sources. It also contains a template fallback response.
  - `ToolContext` — structured container passed to the LLM; includes yard_state, predictions, rag_documents, trailer_lookup, user_intent, and entities.

- **[app/ai/intent_router.py](app/ai/intent_router.py)**
  - Pure intent classifier and tool selection.
  - `IntentRouter.classify()` computes scores from keyword and regex patterns, extracts entities (trailer IDs, zones, numbers, carriers), and returns an `Intent` object.
  - `IntentRouter.route()` produces `RouteResult` with `tools` (names like `congestion_prediction`, `rag_retrieval`) and `needs_yard_state` flag.

- **[app/ai/tool_executor.py](app/ai/tool_executor.py)**
  - `ToolExecutor.execute(tool_name, yard_state, entities, user_role)` — central dispatcher that runs tool implementations and returns `ToolOutput` (tool_name, data, success, error_message).
  - Tool implementations include:
    - `run_congestion_prediction` — predicts for all zones (or a specific zone) and assembles alerts, highest risk zone, and predictions per zone.
    - `run_sla_prediction` — analyzes breached trailers and returns SLA cards + counts.
    - `run_global_risk_prediction` — runs the global intelligence engine across all zones.
    - `run_trailer_lookup` — a mock lookup for trailer metadata (demo DB in-code; replace with real DB for production).
    - `run_rag_retrieval` — calls `RAGStore.retrieve()` to fetch documents and returns structured doc snippets.

- **[app/ai/rag_store.py](app/ai/rag_store.py)**
  - Implements a local RAG: `RAGStore` uses a `LocalEmbedder` (sentence-transformers) + ChromaDB for persistent chunk storage and Ollama for LLM generation (legacy mode).
  - `LocalEmbedder` wraps `SentenceTransformer` and exposes `embed_documents` and `embed_query` methods in a Chroma-compatible way.
  - `RAGStore.add_doc()` splits docs into chunks, extracts simple entities (zones, trailers), and upserts chunks into the `yard_knowledge` collection.
  - `RAGStore.retrieve(query, role, top_k)` validates the DB, computes query embeddings, queries Chroma with embeddings (and role-based filtering), boosts matches for zone/trailer overlap, and returns deduplicated `RetrievedContext` entries used by the assistant.
  - `init_knowledge(store)` seeds a small set of default `KnowledgeDoc` entries at startup.

- **[app/routes/assistant.py](app/routes/assistant.py)**
  - Exposes an AI chat endpoint: `POST /chat` accepts `message`, `user_role`, optional `yard_context` and returns the assistant response, intent metadata, and tool_context for debugging.
  - Also includes `/history/{session_id}` and DELETE `/history/{session_id}` to manage chat sessions.

**Runtime Notes & Integrations**
- The ML model is loaded at import time by `app/services/congestion.py` from `app/ml_models/best_model.pkl`. Train with `python app/train_congestion_model.py` if the model is missing.
- The AI assistant expects a local Ollama instance (or change `LLMResponseGenerator` to another provider). The RAG uses `sentence-transformers` and ChromaDB; ensure embeddings and Chroma persist directory (`CHROMA_DIR`) are writable.
- The trailer lookup in `ToolExecutor.run_trailer_lookup` is a hardcoded demo map — replace with a real datastore for production.

**How to use**
- Start backend API:
```bash
uvicorn main:app --reload
```
- Chat with YardBuddy via `POST /api/ai/chat` or use prediction endpoints under `/predict/*` from `app/routes/congestion.py`.

**Suggested Next Steps**
- Replace demo trailer DB in `app/ai/tool_executor.py` with a real query to your asset database.
- Add authentication/authorization around the AI endpoints and RAG retrieval.
- Add unit tests for `IntentRouter` scoring and `ToolExecutor` tool outputs.
- Consider lazy-loading the ML model to speed API import time, or move model load to startup event.

If you'd like, I can:
- run tests or lints now; or
- generate a README summary and endpoint examples; or
- convert this documentation into rendered HTML pages.
