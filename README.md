# 🚛 YardBuddy – AI-Powered Yard Management System (YMS)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![LangChain](https://img.shields.io/badge/LangChain-Agentic%20Framework-orange)
![Ollama](https://img.shields.io/badge/Ollama-Llama3%20Local%20LLM-black)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Database-purple)
![XGBoost](https://img.shields.io/badge/XGBoost-ML-yellow)
![React](https://img.shields.io/badge/React-Frontend-blue)
![Status](https://img.shields.io/badge/Status-Active-success)

YardBuddy is an **AI-powered, agentic Yard Management System** that combines  
**predictive analytics, Retrieval-Augmented Generation (RAG), and a local LLM**  
to enable **real-time operational intelligence in logistics yards**.

The system is designed as a **decision-support platform**, not just a chatbot —  
helping teams anticipate risks, optimize operations, and access knowledge instantly.

---

## 🚀 Overview

Logistics yard operations are often **reactive and fragmented**:
- Congestion is identified too late  
- SLA breaches are detected after impact  
- Business teams depend on analysts for insights  
- Operational knowledge is scattered across documents  

YardBuddy solves this by integrating:

- 📊 **Predictive Intelligence** → congestion, SLA risk, yard health  
- 📘 **Knowledge Intelligence (RAG)** → policies, SLA rules, guides  
- 💬 **Conversational AI** → natural language interaction  
- ⚙️ **Agentic Orchestration** → intent-driven system execution  

---

## 🧠 Key Features

### 🔹 Agentic Query Routing
- Detects **user intent dynamically**
- Routes queries to:
  - Predictive engine (data-driven)
  - RAG pipeline (knowledge-driven)

---

### 🔹 Predictive Intelligence Layer
- Zone-level congestion prediction  
- SLA breach detection  
- Global yard risk scoring  
- Utilization forecasting  

Outputs:
- Risk levels (LOW / MEDIUM / HIGH)  
- Forecast windows  
- Mitigation recommendations  

---

### 🔹 Knowledge Intelligence (RAG)

- Policy documents (SLA rules, operational guides):
  - Split into chunks  
  - Embedded using **SentenceTransformer (all-MiniLM-L6-v2)**  
- Stored in **ChromaDB vector database** with metadata  

Query Flow:
1. User query → embedding  
2. Similarity search via ChromaDB  
3. Retrieve relevant chunks  
4. Pass context to LLM  
5. Generate grounded response  

---

### 🔹 Floating LLM Architecture

- LLM is not standalone — it operates on:
  - Live yard data  
  - ML predictions  
  - Retrieved knowledge  

Ensures:
- Grounded outputs  
- Reduced hallucination  
- Context-aware responses  

---

### 🔹 Context Aggregation Engine
Combines:
- Live yard state  
- Prediction outputs  
- RAG documents  

→ Passed to LLM for final reasoning

---

## 🏗️ System Architecture

1. User Query  
2. Intent Router  
3. Tool Selection  
4. Execution Layer  
   - Predictive Engine  
   - RAG Retrieval  
5. Context Aggregation  
6. LLM Reasoning (Llama3 via Ollama)  
7. Response Generation  

---

## 🧩 Tech Stack

| Layer | Technology |
|------|-----------|
| Backend API | FastAPI |
| LLM | Llama3 (Ollama – Local) |
| Agent Framework | LangChain |
| RAG | ChromaDB |
| Embeddings | SentenceTransformers |
| ML Models | XGBoost |
| Frontend | React |
| Orchestration | Custom Intent Router + Tool Executor |

---

## 🔌 API Overview

### 🤖 AI Chat

```http
POST /api/ai/chat

Request:

{
  "message": "What is the current yard status?",
  "user_role": "supervisor"
}
📊 Prediction APIs
POST /predict/congestion
POST /predict/global-yard-risk
POST /predict/sla-risk
🧪 Health Check
GET /health/ai
⚙️ Setup Instructions
1. Clone Repository
git clone https://github.com/your-username/yms.git
cd yms
2. Create Virtual Environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
3. Install Dependencies
pip install -r requirements.txt
4. Start Local LLM (Ollama)
ollama run llama3
5. Run Backend
uvicorn main:app --reload
6. (Optional) Train ML Model
python app/train_congestion_model.py
💬 Example Queries
“What is the current yard status?”
“Which zone has highest congestion risk?”
“Which trailers are breaching SLA?”
“What is the SLA dwell time policy?”
🔐 Design Principles
Read-only execution (no destructive queries)
Schema-aware system behavior
Grounded responses via RAG
Intent-based routing for reliability
🚀 Future Scope
1. Real-Time Data Integration

Integrate IoT sensors and live telemetry for real-time yard state.

2. Role-Based Access Control (RBAC)

Restrict data visibility based on user roles (Ops, Finance, Admin).

3. Fuzzy Query Understanding

Handle ambiguous queries (e.g., “Food” → “Groceries”-like mapping).

4. Production Data Integration

Replace mock trailer lookup with real database systems.

5. Advanced Analytics Dashboard

Interactive UI for predictive insights and historical trends.
