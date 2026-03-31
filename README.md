# 🚛 YardBuddy – AI-Powered Yard Management System (YMS)

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![LangChain](https://img.shields.io/badge/LangChain-Agentic%20Framework-orange)
![Ollama](https://img.shields.io/badge/Ollama-Llama3%20Local%20LLM-black)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20Database-purple)
![XGBoost](https://img.shields.io/badge/XGBoost-ML-yellow)
![React](https://img.shields.io/badge/React-Frontend-blue)
![Status](https://img.shields.io/badge/Status-Active-success)

YardBuddy is an **AI-powered, agentic Yard Management System** that combines **predictive analytics, Retrieval-Augmented Generation (RAG), and a local LLM** to enable **real-time operational intelligence in logistics yards**.

The system is designed as a **decision-support platform**, not just a chatbot -
helping teams anticipate risks, optimize operations, and access knowledge instantly.


<img width="863" height="1079" alt="image" src="https://github.com/user-attachments/assets/79beda53-af6d-4a00-baad-f112b174dabd" />


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
<img width="691" height="486" alt="image" src="https://github.com/user-attachments/assets/743fb8d0-d25b-403d-b5f2-2ff8c6a275ce" />
<img width="685" height="482" alt="image" src="https://github.com/user-attachments/assets/4e0a612f-7af9-4fee-b1f9-683136087c4c" />
<img width="685" height="481" alt="image" src="https://github.com/user-attachments/assets/8b492df2-c5a0-4fd6-933b-89f92520fc5c" />
<img width="192" height="312" alt="image" src="https://github.com/user-attachments/assets/caf153d9-c884-498e-8ecd-70190370af05" />
<img width="373" height="286" alt="image" src="https://github.com/user-attachments/assets/dea5a82e-8088-4e85-8dc9-5bf00f40e030" />




---

