"""
Conversational RAG with Query Rewriting Engine for Autorag_champs.

Features:
1. Multi-Turn History Tracking: Preserves rolling dialogue history across user and assistant turns.
2. Follow-Up Query Rewriter: Prompts LLM to rewrite ambiguous follow-up questions into standalone search queries using dialogue context.
3. Standalone Vector Retrieval: Uses rewritten query for vector search to ensure accurate context retrieval.
4. Grounded Conversational Generation: Responds naturally to original user follow-ups while citing source evidence ([1], [2]).
5. Rolling History Management: Balances token limits and prevents context drift.
"""

import os
import sys
import math
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Configure logging with UTF-8 stream handler to support all environments
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "conversational_rag_demo.log")

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

class ConversationalRAGEngine:
    def __init__(self, min_top_score: float = 0.50, max_history_turns: int = 6):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")
        self.model = os.getenv("CHAT_MODEL", "openai/gpt-4o-mini")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.min_top_score = min_top_score
        self.max_history_turns = max_history_turns
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

    def rewrite_followup(self, history: list, user_question: str) -> str:
        """
        Prompts the LLM to inspect dialogue history and rewrite an ambiguous follow-up
        into a self-contained standalone search query.
        """
        if not history:
            return user_question

        formatted_history = "\n".join(
            f"{turn['role'].capitalize()}: {turn['content']}" for turn in history[-self.max_history_turns:]
        )

        system_prompt = (
            "You are a search query reformulation assistant.\n"
            "Given the conversation history and a follow-up user question, rewrite the follow-up question into a single, self-contained standalone search query.\n"
            "Rules:\n"
            "1. Use the conversation history ONLY to resolve ambiguous terms, pronouns ('it', 'that'), or fault codes.\n"
            "2. Do NOT answer the question.\n"
            "3. Return ONLY the rewritten standalone query string with no extra prose."
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
            # Strip quotes if generated
            if (rewritten.startswith('"') and rewritten.endswith('"')) or (rewritten.startswith("'") and rewritten.endswith("'")):
                rewritten = rewritten[1:-1]
            return rewritten
        except Exception as e:
            logging.error("Failed query rewrite for '%s': %s", user_question, e)
            return user_question

    def conversational_answer(self, history: list, user_question: str, k: int = 4) -> dict:
        """
        Processes a multi-turn conversational RAG turn:
        1. Rewrites user_question into a standalone query if history exists.
        2. Retrieves candidate chunks using standalone query.
        3. Applies guardrail check (MIN_TOP_SCORE = 0.65).
        4. Generates grounded answer with source citations.
        5. Updates history with new user & assistant turns.
        """
        standalone_query = self.rewrite_followup(history, user_question)
        chunks = self.retrieve_chunks(standalone_query, k=k)
        top_score = chunks[0]["score"] if chunks else 0.0

        # Guardrail check
        if not chunks or top_score < self.min_top_score:
            answer = "I don't have enough reliable context in the service manuals to answer that."
            history.append({"role": "user", "content": user_question})
            history.append({"role": "assistant", "content": answer})
            return {
                "original_question": user_question,
                "rewritten_query": standalone_query,
                "answer": answer,
                "sources": [],
                "top_score": round(top_score, 4),
                "status": "refused_weak_context"
            }

        strong_chunks = [c for c in chunks if c["score"] >= self.min_top_score]
        sources = sorted(list(set(c["metadata"]["source"] for c in strong_chunks)))

        context_blocks = []
        for idx, c in enumerate(strong_chunks, start=1):
            context_blocks.append(f"[{idx}] (Source: {c['metadata']['source']} | Section: {c['metadata']['section']})\n{c['text']}")
        context_str = "\n\n".join(context_blocks)

        system_prompt = (
            "You are an expert automotive diagnostic assistant.\n"
            "Answer the user's question using ONLY the provided Context below.\n"
            "Cite every factual claim using source markers like [1] or [2].\n"
            "If the Context does not support an answer, state that you do not have enough information."
        )
        user_prompt = f"Context:\n{context_str}\n\nQuestion: {user_question}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            answer = response.choices[0].message.content.strip()

            # Append to rolling history
            history.append({"role": "user", "content": user_question})
            history.append({"role": "assistant", "content": answer})

            return {
                "original_question": user_question,
                "rewritten_query": standalone_query,
                "answer": answer,
                "sources": sources,
                "top_score": round(top_score, 4),
                "status": "answered"
            }

        except Exception as e:
            logging.error("Failed generation for '%s': %s", user_question, e)
            return {
                "original_question": user_question,
                "rewritten_query": standalone_query,
                "answer": f"Error generating answer: {e}",
                "sources": sources,
                "top_score": round(top_score, 4),
                "status": "generation_error"
            }

def run_conversational_rag_demo():
    engine = ConversationalRAGEngine(min_top_score=0.50)

    logging.info("=" * 80)
    logging.info("STARTING CONVERSATIONAL RAG & QUERY REWRITING DEMO")
    logging.info("Model: %s | Max History Turns: %d", engine.model, engine.max_history_turns)
    logging.info("=" * 80)

    history = []

    dialogue_turns = [
        "What is the diagnostic troubleshooting procedure for DTC P0300 on 2023 SUV Model X?",
        "What connector should I inspect for misfire issues?",
        "What primary resistance specification should it measure?",
        "What is the refund policy for customer sales invoice #8891?"
    ]

    for turn_idx, question in enumerate(dialogue_turns, start=1):
        logging.info("\n" + "=" * 80)
        logging.info("--- MULTI-TURN DIALOGUE TURN #%d ---", turn_idx)
        logging.info("User Original Question: '%s'", question)

        res = engine.conversational_answer(history, question)

        logging.info("  Rewritten Standalone Query: '%s'", res["rewritten_query"])
        logging.info("  Retrieval Status: %s | Top Score: %.4f", res["status"], res["top_score"])
        logging.info("  Sources Used: %s", res["sources"])
        logging.info("  Assistant Response:\n    \"%s\"", res["answer"])

    logging.info("\n" + "=" * 80)
    logging.info("FINAL CONVERSATION HISTORY OBJECT (%d Turns Recorded)", len(history))
    logging.info("=" * 80)
    for idx, turn in enumerate(history, start=1):
        logging.info("Turn #%d [%s]: %s", idx, turn["role"].upper(), turn["content"][:100])

    logging.info("=" * 80)
    logging.info("CONVERSATIONAL RAG DEMO COMPLETED. Log saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_conversational_rag_demo()
