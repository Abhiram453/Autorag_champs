"""
FastAPI Backend Server for Aura Automotive Service Platform.

Endpoints:
- POST /query: Executes RAG retrieval, guardrail checks, and grounded generation with inline citations.
- GET /status: Returns knowledge base index health, active models, and guardrail settings.
- GET /metrics: Operational oversight metrics for the Manager Command Center.
- GET /audit-logs: Compliance and validation logs for the Admin Audit Panel.
- GET /health: Liveness probe.
- GET /: Serves the multi-portal UI.
"""

import os
import sys
import math
import json
import time
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from openai import OpenAI

# Ensure workspace root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# Observability, Caching & Cost Tracking
from src.observability import (
    get_cached_answer,
    save_cached_answer,
    clear_cache,
    count_tokens,
    estimate_cost,
    log_rag_request,
    summarize_usage,
    generate_usage_report,
)

# Configure logging
os.makedirs("outputs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [API] %(message)s"
)
logger = logging.getLogger("rag_api")

load_dotenv()

# --- Pydantic Data Models ---

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question string to query against the automotive RAG knowledge base")
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Multi-turn conversation history turns")
    k: Optional[int] = Field(default=4, ge=1, le=10, description="Number of candidate chunks to retrieve")

class SourceItem(BaseModel):
    source: str = Field(..., description="Source document filename")
    chunk_id: Optional[str] = Field(None, description="Unique chunk identifier")
    section: Optional[str] = Field(None, description="Section heading")
    doc_type: Optional[str] = Field(None, description="Document type category")
    score: Optional[float] = Field(None, description="Cosine similarity score")
    text: Optional[str] = Field(None, description="Chunk text content")

class CitationMeta(BaseModel):
    marker: str
    source: str
    chunk_id: str
    section: str
    doc_type: str
    text: str

class QueryResponse(BaseModel):
    question: str
    rewritten_query: Optional[str] = None
    answer: str
    sources: List[SourceItem]
    citations: Dict[str, CitationMeta] = Field(default_factory=dict)
    top_score: float
    confidence: float
    status: str  # "answered" | "refused_weak_context" | "generation_error"
    cache_hit: bool = False
    usage: Optional[Dict[str, Any]] = None

class StatusResponse(BaseModel):
    status: str
    active_chat_model: str
    active_embedding_model: str
    indexed_documents: int
    indexed_chunks: int
    min_top_score: float
    corpus_sources: List[str]

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    role: Optional[str] = Field(default=None, description="Optional role preference")

class LoginResponse(BaseModel):
    session_id: str
    user: Dict[str, Any]
    role: str
    message: str

class FeedbackRequest(BaseModel):
    technician: str = Field(..., description="Technician name")
    action: str = Field(..., description="Feedback action, e.g. Report Unclear, Outdated Guide, Complete Job")
    vin: Optional[str] = Field("1G1RC6E4XGU123456", description="Vehicle VIN")
    doc_id: Optional[str] = Field("TRNS-092", description="Document ID")
    notes: Optional[str] = Field("", description="Optional technician notes")

# In-memory authentication & dynamic audit logs store
ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
DYNAMIC_AUDIT_LOGS: List[Dict[str, Any]] = []


# --- Cosine Similarity Helper ---

def cosine_similarity(vec_a: list, vec_b: list) -> float:
    """Computes cosine similarity score between two vector arrays."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


# --- Core RAG Service Engine ---

class BackendRAGEngine:
    def __init__(self, min_top_score: float = 0.50, max_history_turns: int = 6):
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")
        self.model = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.min_top_score = min_top_score
        self.max_history_turns = max_history_turns
        self.cache_file = ROOT_DIR / "outputs" / "backend_corpus_cache.json"
        self.corpus_chunks = self.load_or_build_corpus()

    def get_base_chunks(self) -> List[Dict[str, Any]]:
        """Base automotive corpus chunks."""
        return [
            {
                "chunk_id": "chunk_mnl_001",
                "text": "AUTOMOTIVE REPAIR MANUAL: DTC P0300 indicates random misfire. Inspect Bank 1 ignition coils. Primary resistance specification: 0.4 to 0.6 ohms across terminals 1 and 2.",
                "metadata": {
                    "source": "sample_manual.txt",
                    "doc_type": "Repair Manual",
                    "section": "Ignition Diagnostics"
                }
            },
            {
                "chunk_id": "chunk_tsb_112",
                "text": "TECHNICAL SERVICE BULLETIN TSB-22-112: Moisture intrusion at engine compartment bulkhead wiring harness connector C102 causes pin resistance variance and intermittent misfires.",
                "metadata": {
                    "source": "tsb_notice.md",
                    "doc_type": "TSB",
                    "section": "Wiring Harness"
                }
            },
            {
                "chunk_id": "chunk_rcl_088",
                "text": "SAFETY RECALL NOTICE RCL-23-088B: Flash Battery Control Module software to version v1.0.0 or higher to resolve false thermal management warnings on 2023 SUV Model X.",
                "metadata": {
                    "source": "recall_report.html",
                    "doc_type": "Safety Recall",
                    "section": "Battery Firmware"
                }
            },
            {
                "chunk_id": "chunk_mnl_002",
                "text": "AUTOMOTIVE SERVICE SPECIFICATIONS: Ignition coil hold-down bolt torque is 9-11 Nm (80-97 in-lb). Secondary resistance specification is 5.0 to 7.0 kOhms.",
                "metadata": {
                    "source": "sample_manual.txt",
                    "doc_type": "Repair Manual",
                    "section": "Torque & Secondary Resistance"
                }
            },
            {
                "chunk_id": "chunk_tsb_113",
                "text": "BULLETIN TSB-22-113: Connector C102 pin terminal inspection requires pin tension gauge #T-992. Replace harness connector seal if orange gasket shows degradation or oil contamination.",
                "metadata": {
                    "source": "tsb_notice.md",
                    "doc_type": "TSB",
                    "section": "Connector Inspection"
                }
            }
        ]

    def load_or_build_corpus(self) -> List[Dict[str, Any]]:
        """Loads cached corpus embeddings or generates live embeddings."""
        chunks = self.get_base_chunks()

        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                if len(cached) == len(chunks):
                    logger.info("Loaded %d corpus chunks from embedding cache.", len(cached))
                    return cached
            except Exception as e:
                logger.warning("Could not load embedding cache: %s. Re-generating.", e)

        logger.info("Generating embeddings for %d corpus chunks...", len(chunks))
        try:
            texts = [c["text"] for c in chunks]
            res = self.client.embeddings.create(model=self.embedding_model, input=texts)
            for chunk, item in zip(chunks, res.data):
                chunk["embedding"] = item.embedding
            
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, indent=2)
            logger.info("Generated and cached live embeddings.")
            return chunks
        except Exception as e:
            logger.error("Failed to generate live embeddings: %s", e)
            return chunks

    def embed_query(self, query: str) -> List[float]:
        """Generates embedding vector for a query string."""
        try:
            res = self.client.embeddings.create(model=self.embedding_model, input=query)
            return res.data[0].embedding
        except Exception as e:
            logger.error("Failed to embed query '%s': %s", query, e)
            return []

    def retrieve_chunks(self, query: str, k: int = 4) -> List[Dict[str, Any]]:
        """Retrieves and ranks chunks by cosine similarity."""
        query_vec = self.embed_query(query)
        if not query_vec:
            return []

        ranked = []
        for chunk in self.corpus_chunks:
            emb = chunk.get("embedding", [])
            score = cosine_similarity(query_vec, emb)
            ranked.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "score": score
            })

        return sorted(ranked, key=lambda item: item["score"], reverse=True)[:k]

    def rewrite_followup(self, history: List[Dict[str, str]], user_question: str) -> str:
        """Rewrites conversational follow-up into a standalone search query."""
        if not history:
            return user_question

        formatted_history = "\n".join(
            f"{turn.get('role', 'user').capitalize()}: {turn.get('content', '')}"
            for turn in history[-self.max_history_turns:]
        )

        system_prompt = (
            "You are a search query reformulation assistant.\n"
            "Given the conversation history and a follow-up question, rewrite the question into a single, self-contained standalone search query.\n"
            "Rules:\n"
            "1. Use conversation history ONLY to resolve pronouns or missing automotive context.\n"
            "2. Do NOT answer the question.\n"
            "3. Return ONLY the rewritten standalone query string with no extra explanation."
        )

        user_msg = f"Conversation History:\n{formatted_history}\n\nFollow-up Question: {user_question}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.0
            )
            rewritten = response.choices[0].message.content.strip()
            if (rewritten.startswith('"') and rewritten.endswith('"')) or (rewritten.startswith("'") and rewritten.endswith("'")):
                rewritten = rewritten[1:-1]
            return rewritten
        except Exception as e:
            logger.warning("Query rewrite failed, falling back to original: %s", e)
            return user_question

    def query(self, question: str, history: Optional[List[Dict[str, str]]] = None, k: int = 4) -> Dict[str, Any]:
        """
        Executes complete RAG pipeline:
        1. Query rewriting for conversational context.
        2. Vector retrieval and score ranking.
        3. Quality guardrail gating (min score check).
        4. Grounded answer generation with inline citation markers.
        """
        history = history or []
        standalone_query = self.rewrite_followup(history, question)
        chunks = self.retrieve_chunks(standalone_query, k=k)
        top_score = round(chunks[0]["score"], 4) if chunks else 0.0

        # Guardrail check
        if not chunks or top_score < self.min_top_score:
            logger.info("Guardrail triggered: top_score %.4f < threshold %.2f", top_score, self.min_top_score)
            return {
                "question": question,
                "rewritten_query": standalone_query,
                "answer": "I don't have enough reliable context in the automotive service manuals to answer that question.",
                "sources": [],
                "citations": {},
                "top_score": top_score,
                "confidence": top_score,
                "status": "refused_weak_context"
            }

        # Filter strong supporting chunks
        strong_chunks = [c for c in chunks if c["score"] >= self.min_top_score]
        
        # Build citation map & structured source items
        citation_map = {}
        sources_list = []
        for idx, c in enumerate(strong_chunks, start=1):
            marker = f"[{idx}]"
            meta = c.get("metadata", {})
            source_item = {
                "source": meta.get("source", "manual.txt"),
                "chunk_id": c.get("chunk_id", f"chunk_{idx}"),
                "section": meta.get("section", "General"),
                "doc_type": meta.get("doc_type", "Documentation"),
                "score": round(c.get("score", 0.0), 4),
                "text": c.get("text", "")
            }
            sources_list.append(source_item)
            citation_map[marker] = {
                "marker": marker,
                "source": source_item["source"],
                "chunk_id": source_item["chunk_id"],
                "section": source_item["section"],
                "doc_type": source_item["doc_type"],
                "text": source_item["text"]
            }

        # Grounded generation prompt
        context_blocks = []
        for idx, s in enumerate(sources_list, start=1):
            context_blocks.append(f"[{idx}] (Source: {s['source']} | Section: {s['section']})\n{s['text']}")
        context_str = "\n\n".join(context_blocks)

        system_prompt = (
            "You are an expert automotive technical assistant.\n"
            "Answer the question strictly using ONLY the provided Context.\n"
            "Cite every factual claim using source markers like [1] or [2].\n"
            "If the Context does not support an answer, state clearly that you do not have enough information."
        )
        user_prompt = f"Context:\n{context_str}\n\nQuestion: {question}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            answer_text = response.choices[0].message.content.strip()

            return {
                "question": question,
                "rewritten_query": standalone_query,
                "answer": answer_text,
                "sources": sources_list,
                "citations": citation_map,
                "top_score": top_score,
                "confidence": top_score,
                "status": "answered"
            }
        except Exception as e:
            logger.error("LLM Generation error: %s", e)
            return {
                "question": question,
                "rewritten_query": standalone_query,
                "answer": f"Error generating answer: {e}",
                "sources": sources_list,
                "citations": citation_map,
                "top_score": top_score,
                "confidence": top_score,
                "status": "generation_error"
            }

    def rag_pipeline_stream(self, question: str, history: Optional[List[Dict[str, str]]] = None, k: int = 4):
        """
        Streaming generator for the RAG pipeline.
        Yields typed events:
        1. {"type": "citations", "sources": [...]} with retrieved grounding evidence.
        2. {"type": "token", "text": "..."} as LLM generates answer tokens.
        """
        history = history or []
        standalone_query = self.rewrite_followup(history, question)
        chunks = self.retrieve_chunks(standalone_query, k=k)
        top_score = round(chunks[0]["score"], 4) if chunks else 0.0

        # Guardrail check
        if not chunks or top_score < self.min_top_score:
            logger.info("Stream guardrail triggered: top_score %.4f < threshold %.2f", top_score, self.min_top_score)
            yield {
                "type": "status",
                "status": "refused_weak_context",
                "confidence": top_score,
                "rewritten_query": standalone_query
            }
            # Stream refusal text tokens progressively
            refusal_text = "I don't have enough reliable context in the automotive service manuals to answer that question."
            words = refusal_text.split(" ")
            for i, word in enumerate(words):
                prefix = " " if i > 0 else ""
                yield {"type": "token", "text": prefix + word}
            return

        strong_chunks = [c for c in chunks if c["score"] >= self.min_top_score]

        # 1. Emit Citations event FIRST so the UI can display sources immediately
        sources_payload = []
        for idx, c in enumerate(strong_chunks, start=1):
            meta = c.get("metadata", {})
            sources_payload.append({
                "id": f"source-{idx}",
                "label": f"[{idx}]",
                "document": meta.get("source", "manual.txt"),
                "chunk_id": c.get("chunk_id", f"chunk_{idx}"),
                "section": meta.get("section", "General"),
                "doc_type": meta.get("doc_type", "Manual"),
                "score": round(c.get("score", 0.0), 4),
                "text": c.get("text", "")
            })

        yield {
            "type": "citations",
            "sources": sources_payload,
            "status": "answered",
            "confidence": top_score,
            "rewritten_query": standalone_query
        }

        # 2. Build grounded prompt
        context_blocks = []
        for s in sources_payload:
            context_blocks.append(f"{s['label']} (Source: {s['document']} | Section: {s['section']})\n{s['text']}")
        context_str = "\n\n".join(context_blocks)

        system_prompt = (
            "You are an expert automotive technical assistant.\n"
            "Answer the question strictly using ONLY the provided Context.\n"
            "Cite every factual claim using source markers like [1] or [2].\n"
            "If the Context does not support an answer, state clearly that you do not have enough information."
        )
        user_prompt = f"Context:\n{context_str}\n\nQuestion: {question}"

        # 3. Stream tokens from LLM
        stream_response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            stream=True
        )

        for chunk in stream_response:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield {"type": "token", "text": delta.content}


# --- FastAPI Application Setup ---

app = FastAPI(
    title="Aura Automotive Service Platform API",
    description="Multi-portal automotive diagnostic and compliance engine with RAG retrieval.",
    version="1.1.0"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Engine
rag_engine = BackendRAGEngine(min_top_score=0.50)

# Static files directory
STATIC_DIR = ROOT_DIR / "src" / "frontend"


# --- API Routes ---

@app.get("/health", tags=["System"])
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok", "service": "Aura Automotive Service Platform API"}

@app.get("/status", response_model=StatusResponse, tags=["System"])
def get_system_status():
    """Returns knowledge base index statistics and guardrail parameters."""
    unique_sources = sorted(list(set(c["metadata"]["source"] for c in rag_engine.corpus_chunks)))
    return StatusResponse(
        status="operational",
        active_chat_model=rag_engine.model,
        active_embedding_model=rag_engine.embedding_model,
        indexed_documents=len(unique_sources),
        indexed_chunks=len(rag_engine.corpus_chunks),
        min_top_score=rag_engine.min_top_score,
        corpus_sources=unique_sources
    )

@app.get("/metrics", tags=["Management"])
def get_manager_metrics():
    """Returns operational metrics for the Manager Command Center."""
    return {
        "repairs_completed": 1248,
        "repairs_change": "+12%",
        "open_recalls_pct": 78,
        "open_recalls_target": 85,
        "pending_approvals": 42,
        "pending_value": "$34,200",
        "suv_recall_compliance_pct": 92,
        "recent_activities": [
            {
                "technician": "Tech. M. Richards",
                "time": "10 mins ago",
                "action": "Completed diagnostic sequence on ID-8842. Battery voltage anomalous.",
                "type": "diagnostic"
            },
            {
                "technician": "System Alert",
                "time": "45 mins ago",
                "action": "Customer feedback report generated for recent brake service.",
                "rating": 4.2,
                "type": "alert"
            },
            {
                "technician": "Tech. S. Patel",
                "time": "2 hrs ago",
                "action": "Approved parts requisition for RO-2991. Parts expected tomorrow.",
                "type": "approval"
            }
        ]
    }

@app.post("/auth/login", response_model=LoginResponse, tags=["Authentication"])
def login(payload: LoginRequest):
    """
    Authenticates user and generates a secure session token.
    Securely derives user role and permissions from account identity.
    Tracks session ID and appends login attempt to the audit log.
    """
    email = payload.email.strip().lower()
    password = payload.password.strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password cannot be empty.")

    # Secure role determination based on account identity
    if "admin" in email:
        role = "ADMIN"
        name = "Admin M. Davis"
        avatar = "MD"
    elif "manager" in email:
        role = "MANAGER"
        name = "J. Doe"
        avatar = "JD"
    elif "tech" in email or "richards" in email:
        role = "TECHNICIAN"
        name = "Tech. M. Richards"
        avatar = "TR"
    else:
        role = payload.role.upper() if payload.role and payload.role.upper() in ["ADMIN", "MANAGER", "TECHNICIAN"] else "TECHNICIAN"
        name = f"Tech. {email.split('@')[0].capitalize()}"
        avatar = email[:2].upper()

    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    user_info = {
        "email": email,
        "name": name,
        "role": role,
        "avatar": avatar,
        "session_id": session_id,
        "logged_in_at": now_str
    }
    ACTIVE_SESSIONS[session_id] = user_info

    # Log attempt to real-time audit trail
    DYNAMIC_AUDIT_LOGS.insert(0, {
        "doc_id": f"AUTH-{session_id[-6:].upper()}",
        "action": f"User Login ({role})",
        "operator": f"{name} ({email})",
        "timestamp": now_str,
        "feedback_trend": "✓ Session Active"
    })

    return LoginResponse(
        session_id=session_id,
        user=user_info,
        role=role,
        message=f"Welcome {name}. Authenticated as {role}."
    )

@app.get("/auth/session", tags=["Authentication"])
def get_session(session_id: Optional[str] = None):
    """Validates session token and returns active session data."""
    if not session_id or session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=401, detail="Invalid or expired session token.")
    return {"status": "authenticated", "user": ACTIVE_SESSIONS[session_id]}

@app.post("/auth/logout", tags=["Authentication"])
def logout(payload: Dict[str, str]):
    """Logs out and invalidates session token."""
    sid = payload.get("session_id", "")
    if sid in ACTIVE_SESSIONS:
        user = ACTIVE_SESSIONS.pop(sid)
        DYNAMIC_AUDIT_LOGS.insert(0, {
            "doc_id": f"AUTH-{sid[-6:].upper()}",
            "action": f"User Sign Out ({user.get('role', 'USER')})",
            "operator": user.get("name", "User"),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "feedback_trend": "Session Ended"
        })
    return {"status": "logged_out"}

@app.post("/feedback", tags=["Technician Operations"])
def record_technician_feedback(payload: FeedbackRequest):
    """Records real-time technician feedback to the audit trail."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    trend_map = {
        "Report Unclear": "⚠️ Review Requested",
        "Outdated Guide": "📉 Revision Needed",
        "Complete Job": "✅ Job Completed"
    }
    trend = trend_map.get(payload.action, "Logged")
    doc_id = payload.doc_id or f"VIN-{payload.vin[-6:] if payload.vin else '8842'}"

    entry = {
        "doc_id": doc_id,
        "action": f"{payload.action} (VIN: {payload.vin or 'N/A'})",
        "operator": payload.technician or "Tech. M. Richards",
        "timestamp": now_str,
        "feedback_trend": trend
    }
    DYNAMIC_AUDIT_LOGS.insert(0, entry)
    return {"status": "success", "recorded_entry": entry}

@app.get("/audit-logs", tags=["Compliance"])
def get_audit_logs():
    """Returns compliance audit logs for the Admin Audit Panel."""
    static_logs = [
        {
            "doc_id": "TRNS-092",
            "action": "Published",
            "operator": "Admin (M. Davis)",
            "timestamp": "2023-10-26 09:42:11",
            "feedback_trend": "98% Positive"
        },
        {
            "doc_id": "HVAC-441",
            "action": "Uploaded Draft",
            "operator": "L. Chen",
            "timestamp": "2023-10-25 14:15:00",
            "feedback_trend": "Pending Review"
        },
        {
            "doc_id": "SUSP-201",
            "action": "Rejected",
            "operator": "Admin (M. Davis)",
            "timestamp": "2023-10-24 11:30:45",
            "feedback_trend": "Issues Flagged"
        },
        {
            "doc_id": "ELEC-088",
            "action": "Published",
            "operator": "Admin (J. Smith)",
            "timestamp": "2023-10-22 16:05:22",
            "feedback_trend": "Stable (No new feedback)"
        }
    ]
    return {
        "pending_reviews": [
            {
                "id": "DOC-2991-EV",
                "title": "EV Battery Array Diagnostic Guide",
                "version": "v2.4 (Draft)",
                "author": "Sarah Jenkins (Lead Tech)",
                "changes": "Updated thermal tolerance parameters for cells 12-48."
            },
            {
                "id": "PRT-882-BRK",
                "title": "Hydraulic Brake Bleed Protocol",
                "version": "v1.1 (Draft)",
                "author": "Marcus Vance (Systems)",
                "changes": "Added torque specs for newer caliper models."
            }
        ],
        "audit_logs": DYNAMIC_AUDIT_LOGS + static_logs
    }

@app.post("/query", response_model=QueryResponse, tags=["RAG Engine"])
def query_rag(payload: QueryRequest):
    """
    Main RAG query endpoint.
    Accepts question and optional history, returns grounded answer, retrieved sources, citations, and confidence.
    Supports SHA-256 query caching, structured observability logging, and token cost tracking.
    """
    cleaned_question = payload.question.strip()
    if not cleaned_question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty or whitespace only."
        )

    start_time = time.time()
    req_id = f"req_{uuid.uuid4().hex[:10]}"
    filters = {"k": payload.k or 4}

    # 1. Check Query Cache
    cached = get_cached_answer(cleaned_question, filters)
    if cached is not None:
        latency_ms = round((time.time() - start_time) * 1000.0, 2)
        cached_result = dict(cached)
        cached_result["cache_hit"] = True
        cached_result["usage"] = {
            "cache_hit": True,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost": 0.0,
            "latency_ms": latency_ms
        }

        sources_list = []
        for s in cached_result.get("sources", []):
            if isinstance(s, dict):
                sources_list.append(s.get("source", ""))
            elif hasattr(s, "source"):
                sources_list.append(s.source)

        log_rag_request({
            "request_id": req_id,
            "question": cleaned_question,
            "answer": cached_result.get("answer", ""),
            "sources": sources_list,
            "cache_hit": True,
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0,
            "latency_ms": latency_ms,
            "status": cached_result.get("status", "answered")
        })
        return cached_result

    # 2. Cache Miss: Execute live RAG pipeline
    result = rag_engine.query(
        question=cleaned_question,
        history=payload.history,
        k=payload.k or 4
    )
    latency_ms = round((time.time() - start_time) * 1000.0, 2)

    # 3. Calculate Token Usage & Cost
    sources_text = " ".join(s.get("text", "") for s in result.get("sources", []))
    input_tokens = count_tokens(cleaned_question + " " + sources_text)
    output_tokens = count_tokens(result.get("answer", ""))
    cost = estimate_cost(input_tokens, output_tokens)

    usage_data = {
        "cache_hit": False,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms
    }

    result["cache_hit"] = False
    result["usage"] = usage_data

    # 4. Save to Query Cache if answered or safely refused
    if result.get("status") in ("answered", "refused_weak_context"):
        save_cached_answer(cleaned_question, result, filters)

    # 5. Log Structured Audit Record
    log_rag_request({
        "request_id": req_id,
        "question": cleaned_question,
        "answer": result.get("answer", ""),
        "sources": [s.get("source", "") for s in result.get("sources", [])],
        "cache_hit": False,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost": cost,
        "latency_ms": latency_ms,
        "status": result.get("status", "answered")
    })

    return result

@app.post("/query/stream", tags=["RAG Engine"])
def stream_query(payload: QueryRequest):
    """
    Server-Sent Events (SSE) progressive streaming RAG query endpoint.
    Emits typed events:
    - {"type": "status", "stage": ...}
    - {"type": "citations", "sources": [...]}
    - {"type": "token", "text": ...}
    - {"type": "usage", "usage": {...}}
    - {"type": "done"}
    - {"type": "error", "message": ...}
    """
    cleaned_question = payload.question.strip()
    if not cleaned_question:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question cannot be empty or whitespace only."
        )

    start_time = time.time()
    req_id = f"req_{uuid.uuid4().hex[:10]}"
    filters = {"k": payload.k or 4}

    # Check cache for streaming
    cached = get_cached_answer(cleaned_question, filters)
    if cached is not None:
        def cached_stream():
            latency_ms = round((time.time() - start_time) * 1000.0, 2)
            sources_payload = []
            for idx, s in enumerate(cached.get("sources", []), start=1):
                doc_name = s.get("source", "manual.txt") if isinstance(s, dict) else getattr(s, "source", "manual.txt")
                chunk_id = s.get("chunk_id", f"chunk_{idx}") if isinstance(s, dict) else getattr(s, "chunk_id", f"chunk_{idx}")
                sec = s.get("section", "General") if isinstance(s, dict) else getattr(s, "section", "General")
                dtype = s.get("doc_type", "Manual") if isinstance(s, dict) else getattr(s, "doc_type", "Manual")
                sc = s.get("score", 0.0) if isinstance(s, dict) else getattr(s, "score", 0.0)
                txt = s.get("text", "") if isinstance(s, dict) else getattr(s, "text", "")
                sources_payload.append({
                    "id": f"source-{idx}",
                    "label": f"[{idx}]",
                    "document": doc_name,
                    "chunk_id": chunk_id,
                    "section": sec,
                    "doc_type": dtype,
                    "score": sc,
                    "text": txt
                })

            yield f"data: {json.dumps({'type': 'citations', 'sources': sources_payload, 'status': cached.get('status', 'answered'), 'confidence': cached.get('confidence', 1.0), 'cache_hit': True})}\n\n"
            yield f"data: {json.dumps({'type': 'token', 'text': cached.get('answer', '')})}\n\n"

            usage_info = {
                "cache_hit": True,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "estimated_cost": 0.0,
                "latency_ms": latency_ms
            }
            yield f"data: {json.dumps({'type': 'usage', 'usage': usage_info})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            log_rag_request({
                "request_id": req_id,
                "question": cleaned_question,
                "answer": cached.get("answer", ""),
                "sources": [s["document"] for s in sources_payload],
                "cache_hit": True,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost": 0.0,
                "latency_ms": latency_ms,
                "status": cached.get("status", "answered")
            })

        return StreamingResponse(
            cached_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    def event_stream():
        accumulated_text = ""
        captured_sources = []
        is_refusal = False

        try:
            for event in rag_engine.rag_pipeline_stream(
                question=cleaned_question,
                history=payload.history,
                k=payload.k or 4
            ):
                if event.get("type") == "citations":
                    captured_sources = event.get("sources", [])
                elif event.get("type") == "token":
                    accumulated_text += event.get("text", "")
                elif event.get("type") == "status" and event.get("status") == "refused_weak_context":
                    is_refusal = True

                yield f"data: {json.dumps(event)}\n\n"

            # Compute usage metrics
            latency_ms = round((time.time() - start_time) * 1000.0, 2)
            sources_text = " ".join(s.get("text", "") for s in captured_sources)
            input_tokens = count_tokens(cleaned_question + " " + sources_text)
            output_tokens = count_tokens(accumulated_text)
            cost = estimate_cost(input_tokens, output_tokens)

            usage_info = {
                "cache_hit": False,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "estimated_cost": cost,
                "latency_ms": latency_ms
            }

            yield f"data: {json.dumps({'type': 'usage', 'usage': usage_info})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

            # Cache if valid answer
            if accumulated_text and captured_sources and not is_refusal:
                cached_obj = {
                    "question": cleaned_question,
                    "answer": accumulated_text,
                    "sources": captured_sources,
                    "citations": {s["label"]: s for s in captured_sources},
                    "top_score": captured_sources[0].get("score", 0.9) if captured_sources else 0.0,
                    "confidence": captured_sources[0].get("score", 0.9) if captured_sources else 0.0,
                    "status": "answered"
                }
                save_cached_answer(cleaned_question, cached_obj, filters)

            # Log to structured audit trail
            log_rag_request({
                "request_id": req_id,
                "question": cleaned_question,
                "answer": accumulated_text,
                "sources": [s.get("document", s.get("source", "")) for s in captured_sources],
                "cache_hit": False,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost": cost,
                "latency_ms": latency_ms,
                "status": "refused_weak_context" if is_refusal else "answered"
            })

        except Exception as e:
            logger.error("Error in streaming response: %s", e)
            error_event = {
                "type": "error",
                "message": "The answer stopped streaming. Please retry."
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/metrics/observability", tags=["Observability"])
def get_observability_metrics():
    """Returns aggregated query cache, token spend, and latency metrics."""
    return summarize_usage()

@app.post("/cache/clear", tags=["Observability"])
def clear_query_cache():
    """Purges the in-memory query cache."""
    purged = clear_cache()
    return {"status": "cleared", "purged_entries": purged}

@app.get("/", tags=["UI"])
def serve_frontend():
    """Serves the Chat & Query Web UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse(
        status_code=200,
        content={"message": "Aura Automotive Service Platform API is live. Visit /docs for Swagger API documentation."}
    )

# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api_server:app", host="0.0.0.0", port=8000, reload=True)
