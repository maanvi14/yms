"""
rag_store.py - 100% FREE YardBuddy RAG
Uses Ollama (local LLM) + sentence-transformers (local embeddings)

INTEGRATION: Used by ToolExecutor for rag_retrieval tool
"""

import os
import re
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Any, Sequence
from dataclasses import dataclass, field
from enum import Enum

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
import ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()


class UserRole(Enum):
    YARD_SUPERVISOR = "yard-supervisor"
    JOCKEY = "jockey"
    INSPECTOR = "inspector"
    GATE_OPERATOR = "gate-operator"
    ADMIN = "admin"


class DocType(Enum):
    SLA_POLICY = "sla_policy"
    OPERATIONAL_GUIDE = "operational_guide"
    ZONE_INFO = "zone_info"
    EXCEPTION_RULE = "exception_rule"
    SYSTEM_FEATURE = "system_feature"


@dataclass
class KnowledgeDoc:
    id: str
    content: str
    doc_type: DocType
    title: str
    metadata: Dict = field(default_factory=dict)
    allowed_roles: List[UserRole] = field(default_factory=lambda: list(UserRole))


@dataclass
class RetrievedContext:
    doc: KnowledgeDoc
    score: float
    snippet: str

class LocalEmbedder:
    """ChromaDB-compatible embedding wrapper"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
        print(f"🔧 Loading embedder: {self.model_name}")
        try:
            self.model = SentenceTransformer(self.model_name)
            # Get embedding dimension
            test_embedding = self.model.encode("test")
            self.embedding_dim = len(test_embedding)
            print(f"✅ Embedder ready | Dim: {self.embedding_dim}")
        except Exception as e:
            print(f"🔥 Embedder failed: {e}")
            raise

    # ---- REQUIRED BY CHROMADB ----
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents - returns list of embedding vectors"""
        # Filter out None/empty strings
        valid_texts = [t for t in texts if t and isinstance(t, str) and t.strip()]
        if not valid_texts:
            print("⚠️ embed_documents: no valid texts")
            return []
        
        # Encode returns numpy array of shape (n_texts, embedding_dim)
        embeddings = self.model.encode(valid_texts, convert_to_numpy=True)
        
        # Convert to list of lists
        return embeddings.tolist()

    # ✅ FIXED: Explicit signature that ChromaDB expects
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query - returns single embedding vector (list of floats)"""
        if text is None:
            print("⚠️ embed_query: text is None")
            text = ""
        elif not isinstance(text, str):
            text = str(text)
        
        text = text.strip()
        
        try:
            # For single text, encode returns 1D array
            embedding = self.model.encode(text, convert_to_numpy=True)
            
            # Ensure it's 1D and convert to Python list
            if isinstance(embedding, np.ndarray):
                if embedding.ndim == 1:
                    result = embedding.tolist()
                elif embedding.ndim == 2 and embedding.shape[0] == 1:
                    result = embedding[0].tolist()
                else:
                    result = embedding.flatten().tolist()
            else:
                result = list(embedding) if hasattr(embedding, '__iter__') else [float(embedding)]
            
            # CRITICAL: Verify we return a list of floats, not a single float
            if not isinstance(result, list):
                print(f"🔥 CRITICAL: result is {type(result)}, not list")
                result = [float(result)] if isinstance(result, (int, float)) else list(result)
            
            # Ensure all elements are floats
            result = [float(x) for x in result]
            
            return result
                
        except Exception as e:
            print(f"🔥 embed_query failed: {e}")
            import traceback
            traceback.print_exc()
            # Return zero vector as fallback
            return [0.0] * self.embedding_dim

    # ChromaDB compatibility - handles the case where it's called as a function
    def __call__(self, input):
        """Handle being called directly"""
        if isinstance(input, str):
            return [self.embed_query(input)]
        elif isinstance(input, list):
            return self.embed_documents(input)
        else:
            return [self.embed_query(str(input))]

    def name(self):
        return "local-embedder"


class RAGStore:
    """FREE RAG: Local embeddings + Ollama LLM"""
    
    def __init__(self):
        self.llm_model = os.getenv("LLM_MODEL", "llama3")
        self.persist_dir = os.getenv("CHROMA_DIR", "./chroma_db")
        
        print(f"🔧 RAGStore initializing...")
        print(f"   Persist dir: {self.persist_dir}")
        print(f"   LLM Model: {self.llm_model}")
        
        # Local embedder (FREE)
        self.embed_fn = LocalEmbedder()
        
        # ✅ CHANGE 1 — Make ChromaDB Persistent (CRITICAL)
        print(f"🔧 Initializing ChromaDB at {self.persist_dir}...")
        self.client = chromadb.Client(Settings(
            persist_directory=self.persist_dir,
            anonymized_telemetry=False,
            is_persistent=True
        ))
        
        self.collection = self.client.get_or_create_collection(
            name="yard_knowledge",
            embedding_function=self.embed_fn
        )
        
        print(f"✅ ChromaDB ready | Collection: yard_knowledge")
        
        # Text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=400,
            chunk_overlap=50
        )
        
        self._docs: Dict[str, KnowledgeDoc] = {}
        
        # ✅ DEBUG: Check collection count on init
        count = self.collection.count()
        print(f"📚 Collection count on init: {count}")
        
        print(f"✅ RAGStore ready")
    
    def add_doc(self, doc: KnowledgeDoc) -> bool:
        """Add document to knowledge base"""
        print(f"📝 Adding doc: {doc.id}")
        
        # Check duplicates
        content_hash = hashlib.md5(doc.content.encode()).hexdigest()[:12]
        existing = self._docs.get(doc.id)
        if existing and existing.metadata.get("hash") == content_hash:
            print(f"   ⏭️  Skipping (duplicate): {doc.id}")
            return False
        
        # Chunk
        chunks = self.splitter.split_text(doc.content)
        print(f"   📄 Split into {len(chunks)} chunks")
        
        ids, documents, metadatas = [], [], []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc.id}_{i}"
            ids.append(chunk_id)
            documents.append(f"[{doc.title}] {chunk}")
            
            # Extract entities
            zones = self._extract_zones(chunk)
            trailers = self._extract_trailers(chunk)
            
            # Build metadata - ChromaDB doesn't allow empty lists
            metadata = {
                "doc_id": doc.id,
                "doc_type": doc.doc_type.value,
                "title": doc.title,
                "chunk_idx": i,
                "hash": content_hash,
            }
            
            # Only add roles if not empty
            roles = [r.value for r in doc.allowed_roles]
            if roles:
                metadata["roles"] = roles
            
            # Only add zones/trailers if found
            if zones:
                metadata["zones"] = zones
            if trailers:
                metadata["trailers"] = trailers
            
            metadatas.append(metadata)
        
        try:
            self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            self._docs[doc.id] = doc
            print(f"   ✅ Added '{doc.id}': {len(chunks)} chunks")
            return True
        except Exception as e:
            print(f"   🔥 Failed to add '{doc.id}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _extract_zones(self, text: str) -> List[str]:
        zones = re.findall(r'Zone\s+[A-Z]', text, re.I)
        return list(set(z.upper() for z in zones))
    
    def _extract_trailers(self, text: str) -> List[str]:
        trailers = re.findall(r'TRL-\d{4}', text, re.I)
        return list(set(t.upper() for t in trailers))
    
    # ============================================================
    # MAIN METHOD: Used by ToolExecutor (Floating LLM Architecture)
    # ============================================================
    
    def retrieve(self, query: str, role: UserRole, top_k: int = 4) -> List[RetrievedContext]:
        """
        Retrieve relevant documents for LLM context.
        Called by ToolExecutor.run_rag_retrieval()
        """
        print(f"🔍 RAG RETRIEVE: '{query}' | Role: {role.value}")
        
        # ✅ Validate query
        if not query or not isinstance(query, str) or query.strip() == "":
            print("   ⚠️ Empty query, using default")
            query = "yard operations"
        
        # ✅ CHANGE 2 — Prevent Query When DB Empty (VERY IMPORTANT)
        count = self.collection.count()
        print(f"   📚 Collection count: {count}")
        
        if count == 0:
            print("   ⚠️ Knowledge base empty — indexing not run")
            return []
        
        # Build where clause
        where_clause = {}
        if role.value:
            where_clause["roles"] = {"$contains": role.value}
        
        print(f"   🔎 Querying with where: {where_clause}")
        
        # ✅ DEBUG: Test embedding generation
        try:
            test_embedding = self.embed_fn.embed_query(query)
            print(f"   🔧 Test embedding: {len(test_embedding)} dims, type: {type(test_embedding)}")
            print(f"   🔧 First 5 values: {test_embedding[:5]}")
            print(f"   🔧 All floats? {all(isinstance(x, float) for x in test_embedding)}")
            
            if not isinstance(test_embedding, list):
                print(f"   🔥 ERROR: embedding is not a list, it's {type(test_embedding)}")
                return []
            if len(test_embedding) != self.embed_fn.embedding_dim:
                print(f"   🔥 ERROR: embedding has wrong dimension: {len(test_embedding)} vs {self.embed_fn.embedding_dim}")
                return []
        except Exception as e:
            print(f"   🔥 Test embedding failed: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        try:
            # ✅ WORKAROUND: Pre-compute embeddings and pass them directly
            query_embedding = self.embed_fn.embed_query(query)
            
            # Query using embeddings directly instead of query_texts
            results = self.collection.query(
                query_embeddings=[query_embedding],  # Pass pre-computed embeddings
                n_results=top_k,
                where=where_clause if where_clause else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # ✅ Check if results are valid
            if not results or not results.get('documents') or len(results['documents']) == 0:
                print("   ⚠️ No results returned")
                return []
            
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            dists = results['distances'][0]
            
            print(f"   📊 Raw results: {len(docs)} docs")
            
            all_results = []
            
            for doc, meta, dist in zip(docs, metas, dists):
                score = 1 - dist  # Convert to similarity
                print(f"   📄 Doc: {meta.get('title', 'Unknown')} | Score: {score:.3f}")
                
                # Boost for specific mentions
                query_zones = self._extract_zones(query)
                doc_zones = meta.get('zones', [])
                if any(z in doc_zones for z in query_zones):
                    score += 0.1
                    print(f"      ⬆️ Boosted for zone match")
                
                query_trailers = self._extract_trailers(query)
                doc_trailers = meta.get('trailers', [])
                if any(t in doc_trailers for t in query_trailers):
                    score += 0.15
                    print(f"      ⬆️ Boosted for trailer match")
                
                kd = KnowledgeDoc(
                    id=meta['doc_id'],
                    content=doc,
                    doc_type=DocType(meta['doc_type']),
                    title=meta['title'],
                    metadata=meta
                )
                
                all_results.append(RetrievedContext(
                    doc=kd, 
                    score=min(score, 1.0),
                    snippet=doc[:200] + "..."
                ))
            
            # Deduplicate and sort
            seen = set()
            unique = []
            for r in sorted(all_results, key=lambda x: x.score, reverse=True):
                key = (r.doc.id, r.doc.metadata.get('chunk_idx', 0))
                if key not in seen:
                    seen.add(key)
                    unique.append(r)
            
            print(f"   ✅ Returning {len(unique)} unique results")
            return unique[:top_k]
            
        except Exception as e:
            print(f"   🔥 Retrieval error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # ============================================================
    # LEGACY METHOD: Direct RAG generation (optional, for backward compat)
    # ============================================================
    
    def build_prompt(self, query: str, role: UserRole, contexts: List[RetrievedContext], yard_state: Dict) -> str:
        """Build system prompt for direct generation"""
        
        personas = {
            UserRole.YARD_SUPERVISOR: "You are YardBuddy, expert yard supervisor assistant. Strategic, data-driven.",
            UserRole.JOCKEY: "You are YardBuddy, jockey assistant. Clear steps, safety-focused.",
            UserRole.INSPECTOR: "You are YardBuddy, inspector assistant. Thorough, rule-based.",
            UserRole.GATE_OPERATOR: "You are YardBuddy, gate assistant. Process-focused, efficient."
        }
        
        persona = personas.get(role, "You are YardBuddy, yard assistant.")
        
        # Format context
        context_text = "\n\n".join([
            f"[{i+1}] {ctx.doc.title} (score: {ctx.score:.2f})\n{ctx.snippet}"
            for i, ctx in enumerate(contexts)
        ]) if contexts else "No specific documents found."
        
        # Format yard state
        state_lines = []
        if yard_state.get('trailers'):
            state_lines.append(f"Trailers on-site: {yard_state['trailers']}")
        if yard_state.get('docks'):
            state_lines.append(f"Docks occupied: {yard_state['docks']}/12")
        if yard_state.get('breaches'):
            state_lines.append(f"SLA breaches: {len(yard_state['breaches'])}")
        if yard_state.get('zones'):
            for z, c in yard_state['zones'].items():
                state_lines.append(f"{z}: {c}% capacity")
        
        state_text = "\n".join(state_lines) if state_lines else "Yard operational."
        
        prompt = f"""{persona}

## CURRENT YARD STATE
{state_text}

## RELEVANT KNOWLEDGE
{context_text}

## INSTRUCTIONS
- Answer based ONLY on provided knowledge and yard state
- Be specific: cite trailer IDs (TRL-XXXX), zones, rules
- Keep responses concise (2-4 sentences)
- Include links like [Dashboard](/dashboard) when relevant
- For breaches: state trailer ID, carrier, and action needed

## EXAMPLES
Q: "Any SLA breaches?"
A: "Yes, **TRL-2087** (Schneider) exceeds 12-hour dwell. **TRL-3001** (XPO) has temp deviation. [Dashboard](/dashboard)"

Q: "How to check in?"
A: "Go to **Gate → Check-In**. Enter tractor (TX-XXXX), trailer (TRL-XXXX), select mode, click **Check In**."

Now answer: {query}
"""
        return prompt
    
    def generate(self, query: str, role: UserRole, yard_state: Dict = None) -> Dict:
        """
        LEGACY: Full RAG pipeline with direct LLM generation.
        Kept for backward compatibility. 
        New code uses ToolExecutor + assistant.py LLM generation.
        """
        
        yard_state = yard_state or {}
        
        # Retrieve
        contexts = self.retrieve(query, role)
        print(f"📚 Retrieved {len(contexts)} docs")
        
        # Build prompt
        prompt = self.build_prompt(query, role, contexts, yard_state)
        
        # Generate with Ollama (FREE)
        try:
            print(f"🤖 Generating with {self.llm_model}...")
            response = ollama.chat(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query}
                ],
                options={"temperature": 0.3, "num_predict": 300}
            )
            answer = response['message']['content']
            
        except Exception as e:
            answer = f"Error: {str(e)}. Is Ollama running?"
        
        return {
            "response": answer,
            "sources": [{"title": c.doc.title, "score": round(c.score, 3)} for c in contexts[:3]],
            "model": self.llm_model
        }
    
    def get_stats(self) -> Dict:
        """Get RAG statistics"""
        return {
            "total_chunks": self.collection.count(),
            "persist_directory": self.persist_dir,
            "embedding_model": "all-MiniLM-L6-v2 (local)",
            "llm_model": self.llm_model
        }


# Default knowledge
DEFAULT_DOCS = [
    KnowledgeDoc(
        id="sla_dwell",
        title="SLA: Empty Dwell Time",
        doc_type=DocType.SLA_POLICY,
        content="""SLA Dwell Time Policy: The dwell time policy states that empty trailers must not exceed 12 hours dwell time. A warning is issued at 10 hours. Zone C is monitored hourly due to high utilization.""",
        allowed_roles=[UserRole.YARD_SUPERVISOR, UserRole.INSPECTOR]
    ),
    KnowledgeDoc(
        id="checkin_guide",
        title="Gate Check-In Process",
        doc_type=DocType.OPERATIONAL_GUIDE,
        content="""1. Go to Gate → Check-In. 2. Select mode: Live Unload or Drop. 3. Enter tractor plate TX-4829. 4. Enter trailer ID TRL-1001. 5. Click Check In Vehicle.""",
        allowed_roles=list(UserRole)
    ),
    KnowledgeDoc(
        id="zones",
        title="Yard Zones",
        doc_type=DocType.ZONE_INFO,
        content="""Zone A: 50 trailers, 8 docks. Zone B: 75 trailers, 12 docks. Zone C: 40 trailers TRL-2087 TRL-3001, reefers, often 87% full. Zone D: 100 trailers, long-term storage.""",
        allowed_roles=list(UserRole)
    ),
    KnowledgeDoc(
        id="exceptions",
        title="Exception Handling",
        doc_type=DocType.EXCEPTION_RULE,
        content="""SLA Breach: 12+ hours dwell, notify supervisor. Temperature: reefer outside -18°C to -22°C, alert inspector immediately. Unauthorized: security verification required.""",
        allowed_roles=[UserRole.YARD_SUPERVISOR, UserRole.INSPECTOR]
    )
]


def init_knowledge(store: RAGStore):
    """Initialize default knowledge"""
    print(f"🚀 Initializing knowledge base...")
    count_before = store.collection.count()
    print(f"   Before: {count_before} chunks")
    
    added = 0
    for doc in DEFAULT_DOCS:
        if store.add_doc(doc):
            added += 1
    
    count_after = store.collection.count()
    print(f"   After: {count_after} chunks")
    print(f"✅ Initialized {added}/{len(DEFAULT_DOCS)} docs ({count_after - count_before} new chunks)")


if __name__ == "__main__":
    # Test
    store = RAGStore()
    init_knowledge(store)
    
    result = store.generate(
        query="Any SLA breaches?",
        role=UserRole.YARD_SUPERVISOR,
        yard_state={
            "trailers": 8,
            "docks": "7/12",
            "breaches": [{"id": "TRL-2087"}, {"id": "TRL-3001"}],
            "zones": {"Zone C": 87}
        }
    )
    
    print(f"\n{'='*50}")
    print(f"Q: Any SLA breaches?")
    print(f"A: {result['response']}")
    print(f"Sources: {result['sources']}")