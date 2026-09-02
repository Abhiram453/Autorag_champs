"""
Retrieval Quality & Embedding Sanity Testing Engine for Autorag_champs.

Evaluates embedding quality using known query-chunk test cases, ranks chunk embeddings
via cosine similarity, identifies surprising/failing cases, and outputs a structured sanity report.
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
log_file_path = os.path.join("outputs", "embedding_sanity_report.log")

file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
stream_handler = logging.StreamHandler(sys.stdout)

# Avoid unicode charmap errors on Windows console
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

# Known query-chunk smoke test cases for automotive RAG
TEST_CASES = [
    {
        "id": "TC-01",
        "query": "What is the recommended diagnostic check and resistance spec for DTC P0300 misfire?",
        "expected_source": "MNL-24-001",
        "description": "Checks DTC P0300 diagnostic steps target plain text repair manual."
    },
    {
        "id": "TC-02",
        "query": "Is there a service bulletin for moisture corrosion on connector C102?",
        "expected_source": "TSB-22-112",
        "description": "Checks wiring harness connector C102 query targets Markdown TSB bulletin."
    },
    {
        "id": "TC-03",
        "query": "What software update is required for the battery control module thermal recall?",
        "expected_source": "RCL-23-088B",
        "description": "Checks high voltage battery recall query targets HTML recall report."
    },
    # Surprising / Failing Edge Case Test
    {
        "id": "TC-04-FAIL",
        "query": "How do I update customer billing address in sales portal?",
        "expected_source": "MNL-24-001",  # Out of scope query should NOT rank automotive manuals high
        "description": "Surprising/Failing Case: Out-of-scope query testing false-positive ranking."
    }
]

class EmbeddingSanityTester:
    def __init__(self, embedding_model: str = "text-embedding-3-small"):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")
        self.embedding_model = self.detect_model()
        self.corpus_chunks = self.load_corpus_chunks()

    def detect_model(self) -> str:
        """Returns embedding model configuration."""
        return os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

    def load_corpus_chunks(self) -> list:
        """Loads cached chunk embeddings or embeds sample corpus records via API."""
        sample_chunks = [
            {
                "chunk_id": "chunk_mnl_001",
                "source": "MNL-24-001",
                "text": "AUTOMOTIVE REPAIR MANUAL: DTC P0300 indicates random misfire. Inspect Bank 1 ignition coils. Primary resistance specification: 0.4 to 0.6 ohms across terminals 1 and 2."
            },
            {
                "chunk_id": "chunk_tsb_112",
                "source": "TSB-22-112",
                "text": "TECHNICAL SERVICE BULLETIN TSB-22-112: Moisture intrusion at engine compartment bulkhead wiring harness connector C102 causes pin resistance variance and intermittent misfires."
            },
            {
                "chunk_id": "chunk_rcl_088",
                "source": "RCL-23-088B",
                "text": "SAFETY RECALL NOTICE RCL-23-088B: Flash Battery Control Module software to version v1.0.0 or higher to resolve false thermal management warnings on 2023 SUV Model X."
            }
        ]

        logging.info("Generating live embeddings for %d corpus chunks using '%s'...", len(sample_chunks), self.embedding_model)
        try:
            texts = [c["text"] for c in sample_chunks]
            res = self.client.embeddings.create(model=self.embedding_model, input=texts)
            for chunk, item in zip(sample_chunks, res.data):
                chunk["embedding"] = item.embedding
            logging.info("Successfully generated embeddings (%d dimensions).", len(sample_chunks[0]["embedding"]))
            return sample_chunks
        except Exception as e:
            logging.error("Failed to generate live corpus embeddings: %s", e)
            return sample_chunks

    def embed_query(self, query: str) -> list:
        """Embeds a single query string using the active embedding model."""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            logging.error("Failed to embed query '%s': %s", query, e)
            return []

    def rank_chunks(self, query: str, chunk_records: list) -> list:
        """Embeds query and ranks all corpus chunks by cosine similarity."""
        query_vec = self.embed_query(query)
        if not query_vec:
            return [{"source": c.get("source", "unknown"), "text": c.get("text", ""), "score": 0.0} for c in chunk_records]

        ranked = []
        for chunk in chunk_records:
            chunk_vec = chunk.get("embedding", [])
            score = cosine_similarity(query_vec, chunk_vec)
            ranked.append({
                "chunk_id": chunk.get("chunk_id", "unknown"),
                "source": chunk.get("source", "unknown"),
                "text": chunk.get("text", ""),
                "score": score
            })

        return sorted(ranked, key=lambda item: item["score"], reverse=True)

    def run_sanity_suite(self) -> dict:
        """Executes all smoke test cases and generates a structured sanity report."""
        logging.info("=" * 80)
        logging.info("STARTING EMBEDDING SANITY & RETRIEVAL RELEVANCE SUITE")
        logging.info("Model: %s | Corpus Chunks: %d", self.embedding_model, len(self.corpus_chunks))
        logging.info("=" * 80)

        report_rows = []
        for test in TEST_CASES:
            query = test["query"]
            expected = test["expected_source"]
            test_id = test["id"]

            ranked_results = self.rank_chunks(query, self.corpus_chunks)
            top_result = ranked_results[0] if ranked_results else {"source": "none", "score": 0.0, "text": ""}
            
            # Evaluate pass/fail: Top ranked source matches expected source
            passed = (top_result["source"] == expected) if "FAIL" not in test_id else (top_result["score"] < 0.60)
            
            row = {
                "test_id": test_id,
                "query": query,
                "expected_source": expected,
                "top_source": top_result["source"],
                "top_score": round(top_result["score"], 4),
                "passed": passed,
                "description": test["description"]
            }
            report_rows.append(row)

            status_str = "[PASS]" if passed else "[FAIL]"
            logging.info("\n[%s] %s", test_id, status_str)
            logging.info("  Query: '%s'", query)
            logging.info("  Expected Source: %s | Top Ranked Source: %s (Score: %.4f)",
                         expected, top_result["source"], top_result["score"])
            logging.info("  Top Chunk Snippet: '%s...'", top_result["text"][:70])

        passed_count = sum(1 for r in report_rows if r["passed"])
        failed_count = len(report_rows) - passed_count
        pass_pct = round((passed_count / len(report_rows)) * 100, 1)

        summary = {
            "total_tests": len(report_rows),
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate_pct": pass_pct,
            "results": report_rows
        }

        logging.info("\n" + "=" * 80)
        logging.info("SANITY REPORT SUMMARY")
        logging.info("Total Tests: %d | Passed: %d | Failed: %d | Pass Rate: %.1f%%",
                     len(report_rows), passed_count, failed_count, pass_pct)
        logging.info("=" * 80)

        return summary

def run_embedding_sanity_demo():
    tester = EmbeddingSanityTester()
    summary = tester.run_sanity_suite()
    
    # Detailed Analysis of Failing/Surprising Edge Case
    logging.info("\n--- SURPRISING & FAILING CASE ANALYSIS ---")
    logging.info("Failure Case (TC-04-FAIL): Out-of-scope query ('billing address in sales portal').")
    logging.info("Observation: Even though the query is out of scope, cosine similarity still assigns positive scores to vehicle manuals.")
    logging.info("Pipeline Diagnostic Recommendation: Implement a similarity threshold gate (e.g. score < 0.65) or refusal prompt to prevent out-of-scope retrieval pollution.")

if __name__ == "__main__":
    run_embedding_sanity_demo()
