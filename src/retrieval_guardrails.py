"""
Retrieval Quality Guardrails & Hallucination Prevention Engine for Autorag_champs.

Features:
1. Retrieval Strength Checking: Evaluates retrieved context against score threshold (MIN_TOP_SCORE = 0.70).
2. Pre-Generation Refusal Gating: Prevents LLM invocation when retrieval is weak/empty (status: refused_weak_context).
3. Confident Grounded Generation: Invokes LLM with cited context when evidence is strong (status: answered).
4. Side-by-Side Test Suite: Verifies answerable, out-of-scope, and low-similarity queries.
"""

import os
import sys
import math
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Import citation helper if available
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src.citation_generator import build_cited_prompt, build_citation_map
    HAS_CITATION_HELPER = True
except ImportError:
    HAS_CITATION_HELPER = False

# Configure logging with UTF-8 stream handler to support all environments
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "guardrails_demo.log")

file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
stream_handler = logging.StreamHandler(sys.stdout)

if sys.platform == "win32":
    stream_handler.setStream(open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[stream_handler, file_handler]
)

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

class RetrievalGuardrailsEngine:
    def __init__(self, min_top_score: float = 0.70, min_supporting_chunks: int = 1):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")
        self.model = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.min_top_score = min_top_score
        self.min_supporting_chunks = min_supporting_chunks
        self.corpus_chunks = self.load_corpus()

    def load_corpus(self) -> list:
        """Loads sample automotive corpus chunks enriched with embeddings."""
        chunks = [
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
            }
        ]

        logging.info("Generating live vector embeddings for %d corpus chunks...", len(chunks))
        try:
            texts = [c["text"] for c in chunks]
            res = self.client.embeddings.create(model=self.embedding_model, input=texts)
            for chunk, item in zip(chunks, res.data):
                chunk["embedding"] = item.embedding
            logging.info("Successfully generated embeddings (%d dims).", len(chunks[0]["embedding"]))
            return chunks
        except Exception as e:
            logging.error("Failed to generate live corpus embeddings: %s", e)
            return chunks

    def embed_query(self, query: str) -> list:
        """Embeds a single query string using active embedding model."""
        try:
            response = self.client.embeddings.create(model=self.embedding_model, input=query)
            return response.data[0].embedding
        except Exception as e:
            logging.error("Failed to embed query '%s': %s", query, e)
            return []

    def retrieve_chunks(self, query: str, k: int = 4) -> list:
        """Retrieves and ranks corpus chunks by cosine similarity."""
        query_vec = self.embed_query(query)
        if not query_vec:
            return []

        ranked = []
        for chunk in self.corpus_chunks:
            score = cosine_similarity(query_vec, chunk.get("embedding", []))
            ranked.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
                "score": score
            })

        return sorted(ranked, key=lambda item: item["score"], reverse=True)[:k]

    def retrieval_is_strong(self, chunks: list) -> bool:
        """
        Guardrail check: Evaluates if retrieved chunks meet minimum score thresholds.
        Returns True if at least `min_supporting_chunks` exceed `min_top_score`.
        """
        if not chunks:
            return False
        strong_chunks = [chunk for chunk in chunks if chunk["score"] >= self.min_top_score]
        return len(strong_chunks) >= self.min_supporting_chunks

    def guarded_answer(self, question: str, k: int = 4) -> dict:
        """
        Executes guarded retrieval & generation:
        1. Retrieves top-k candidate chunks.
        2. Evaluates context strength via `retrieval_is_strong`.
        3. If weak/empty: Halts generation before LLM call and returns refusal response.
        4. If strong: Invokes LLM with grounded citation prompt.
        """
        chunks = self.retrieve_chunks(question, k=k)
        top_score = chunks[0]["score"] if chunks else 0.0

        # Guardrail Pre-Generation Refusal Gate
        if not self.retrieval_is_strong(chunks):
            logging.warning("⚠️ Guardrail Triggered! Context too weak for query '%s' (Top Score: %.4f < Threshold %.2f). Halting generation.",
                            question, top_score, self.min_top_score)
            return {
                "question": question,
                "answer": "I don't have enough reliable context to answer that.",
                "sources": [],
                "top_score": round(top_score, 4),
                "status": "refused_weak_context"
            }

        # Context is strong -> Proceed to grounded generation
        strong_chunks = [c for c in chunks if c["score"] >= self.min_top_score]
        sources = sorted(list(set(c["metadata"]["source"] for c in strong_chunks)))

        if HAS_CITATION_HELPER:
            system_prompt, user_prompt = build_cited_prompt(question, strong_chunks)
        else:
            context_str = "\n\n".join(f"[{i+1}] {c['text']}" for i, c in enumerate(strong_chunks))
            system_prompt = "Answer the question strictly using the provided context."
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
                "answer": answer_text,
                "sources": sources,
                "top_score": round(top_score, 4),
                "status": "answered"
            }
        except Exception as e:
            logging.error("Failed LLM generation for query '%s': %s", question, e)
            return {
                "question": question,
                "answer": f"Error during generation: {e}",
                "sources": sources,
                "top_score": round(top_score, 4),
                "status": "generation_error"
            }

def run_guardrails_demo():
    engine = RetrievalGuardrailsEngine(min_top_score=0.70, min_supporting_chunks=1)

    logging.info("=" * 80)
    logging.info("STARTING RETRIEVAL QUALITY GUARDRAILS & HALLUCINATION PREVENTION DEMO")
    logging.info("Model: %s | Min Top Score Threshold: %.2f", engine.model, engine.min_top_score)
    logging.info("=" * 80)

    test_queries = [
        {
            "id": "CASE-1",
            "type": "Answerable Query (Strong Context)",
            "query": "What is the primary resistance specification for Bank 1 ignition coils on DTC P0300?"
        },
        {
            "id": "CASE-2",
            "type": "Unanswerable / Out-of-Scope Query (No Context)",
            "query": "What is the refund policy for a customer sales invoice not in this repair manual?"
        },
        {
            "id": "CASE-3",
            "type": "Low-Similarity Edge Case Query (Weak Context)",
            "query": "How do I fix generic noise coming from somewhere under the vehicle frame?"
        }
    ]

    for test in test_queries:
        logging.info("\n--- [%s] %s ---", test["id"], test["type"])
        logging.info("Question: '%s'", test["query"])

        result = engine.guarded_answer(test["query"])

        logging.info("  Status: %s", result["status"])
        logging.info("  Top Similarity Score: %.4f", result["top_score"])
        logging.info("  Sources Used: %s", result["sources"])
        logging.info("  Final Output Answer:\n    \"%s\"", result["answer"])
        logging.info("-" * 60)

    logging.info("=" * 80)
    logging.info("GUARDRAILS DEMO COMPLETED. Log saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_guardrails_demo()
