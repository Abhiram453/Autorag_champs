"""
Scalable Batch Embedding Pipeline with Exponential Backoff, Idempotent Caching, and Cost Tracking.

Features:
1. Batching: Sends chunks in configurable batch sizes (default: 64) to maximize API throughput.
2. Exponential Backoff: Retries rate-limit (429) and transient network errors (2 ** attempt delay).
3. Idempotent Resumption: Skips already-embedded chunks by checking persistent cache (outputs/batch_embeddings_cache.json).
4. Run Summary & Cost Tracking: Calculates prompt tokens and estimated cost in USD ($0.00002 / 1K tokens).
"""

import os
import sys
import time
import json
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, OpenAIError

# Import TokenEstimator for accurate token counts if available
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from src.token_estimator import TokenEstimator
    HAS_TOKEN_ESTIMATOR = True
except ImportError:
    HAS_TOKEN_ESTIMATOR = False

# Configure logging
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "batch_embedding_pipeline_summary.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

# Price per 1,000 tokens for text-embedding-3-small
PRICE_PER_1K_TOKENS = 0.00002

class BatchEmbeddingPipeline:
    def __init__(self, cache_file: str = "outputs/batch_embeddings_cache.json", embedding_model: str = "text-embedding-3-small"):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")
        self.embedding_model = embedding_model
        self.cache_file = cache_file
        self.cache = self.load_cache()
        self.token_estimator = TokenEstimator() if HAS_TOKEN_ESTIMATOR else None

    def load_cache(self) -> dict:
        """Loads persistent embeddings cache from disk."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logging.info("Loaded %d cached embeddings from '%s'.", len(data), self.cache_file)
                    return data
            except Exception as e:
                logging.warning("Could not read cache file '%s' (%s). Starting fresh.", self.cache_file, e)
        return {}

    def save_cache(self):
        """Saves persistent embeddings cache to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
            logging.info("Saved %d total embeddings to cache '%s'.", len(self.cache), self.cache_file)
        except Exception as e:
            logging.error("Failed to save cache file '%s': %s", self.cache_file, e)

    def count_texts_tokens(self, texts: list) -> int:
        """Counts total tokens for a list of text strings."""
        if self.token_estimator:
            return sum(self.token_estimator.count_tokens(t) for t in texts)
        # Fallback heuristic (~4 chars/token)
        return max(1, sum(int(len(t) / 4) for t in texts))

    def batch_generator(self, items: list, size: int = 64):
        """Yields successive batches of specified size from list."""
        for start in range(0, len(items), size):
            yield items[start : start + size]

    def embed_with_retry(self, texts: list, max_attempts: int = 5):
        """
        Embeds a batch of texts with exponential backoff retry.
        Waits 2 ** attempt seconds after transient/rate-limit failures.
        """
        for attempt in range(max_attempts):
            try:
                response = self.client.embeddings.create(
                    model=self.embedding_model,
                    input=texts
                )
                return response
            except (RateLimitError, APIConnectionError) as error:
                if attempt == max_attempts - 1:
                    logging.error("Max retries reached (%d). Failing batch: %s", max_attempts, error)
                    raise
                wait_seconds = 2 ** attempt
                logging.warning("Transient error (Attempt %d/%d): %s | Waiting %ds...",
                                attempt + 1, max_attempts, error, wait_seconds)
                time.sleep(wait_seconds)
            except Exception as error:
                logging.error("Fatal API Error during embedding batch: %s", error)
                raise

    def process_chunks(self, all_chunks: list, batch_size: int = 64, force_reembed: bool = False) -> dict:
        """
        Processes document chunks through the scalable batch embedding pipeline:
        1. Identifies pending chunks (skips existing cached IDs).
        2. Batches pending chunks into sizes of `batch_size`.
        3. Embeds batches using exponential backoff retry.
        4. Saves vectors to cache and computes token/cost metrics.
        """
        if force_reembed:
            self.cache = {}

        # 1. Filter out already-embedded chunks (Idempotent Caching)
        pending_chunks = [c for c in all_chunks if c["id"] not in self.cache]
        skipped_count = len(all_chunks) - len(pending_chunks)

        summary = {
            "total_chunks": len(all_chunks),
            "skipped_existing": skipped_count,
            "embedded": 0,
            "failed": 0,
            "input_tokens": 0,
            "batches_processed": 0
        }

        logging.info("--- STARTING BATCH EMBEDDING JOB ---")
        logging.info("Total Chunks: %d | Skipped Existing: %d | Pending to Embed: %d | Batch Size: %d",
                     len(all_chunks), skipped_count, len(pending_chunks), batch_size)

        if not pending_chunks:
            logging.info("✅ All %d chunks already exist in cache! Skipping API calls.", len(all_chunks))
            summary["estimated_cost_usd"] = 0.0
            return summary

        # 2. Process pending chunks in batches
        for batch_num, batch in enumerate(self.batch_generator(pending_chunks, batch_size), 1):
            texts = [chunk["text"] for chunk in batch]
            batch_tokens = self.count_texts_tokens(texts)
            summary["input_tokens"] += batch_tokens

            logging.info("Batch #%d: Processing %d chunks (%d tokens)...", batch_num, len(batch), batch_tokens)

            try:
                response = self.embed_with_retry(texts)
                
                # Check response metadata token usage if returned by API
                if hasattr(response, "usage") and response.usage and hasattr(response.usage, "prompt_tokens"):
                    actual_tokens = response.usage.prompt_tokens
                    # Update token count with exact API metadata if available
                    summary["input_tokens"] = summary["input_tokens"] - batch_tokens + actual_tokens

                # 3. Store vectors in cache indexed by chunk ID
                for chunk, data in zip(batch, response.data):
                    self.cache[chunk["id"]] = {
                        "chunk_id": chunk["id"],
                        "source": chunk.get("source", "unknown"),
                        "text": chunk["text"],
                        "embedding": data.embedding
                    }
                
                summary["embedded"] += len(batch)
                summary["batches_processed"] += 1
                self.save_cache()

            except Exception as e:
                summary["failed"] += len(batch)
                logging.error("Batch #%d FAILED: %s", batch_num, e)

        # 4. Compute estimated USD cost
        estimated_cost = (summary["input_tokens"] / 1000.0) * PRICE_PER_1K_TOKENS
        summary["estimated_cost_usd"] = round(estimated_cost, 6)

        logging.info("--- BATCH EMBEDDING JOB COMPLETED ---")
        logging.info("Summary: %s", json.dumps(summary, indent=2))
        logging.info("Estimated Run Cost: $%f USD", summary["estimated_cost_usd"])

        return summary

def run_batch_embedding_demo():
    pipeline = BatchEmbeddingPipeline()

    # Generate sample automotive diagnostic chunks for embedding
    sample_chunks = [
        {"id": "chunk_mnl_001_p01", "source": "MNL-24-001", "text": "DTC P0300 indicates a random or multiple cylinder misfire event detected by ECU."},
        {"id": "chunk_mnl_001_p02", "source": "MNL-24-001", "text": "Step 2: Disconnect negative battery cable and wait 5 minutes before servicing electrical harness."},
        {"id": "chunk_mnl_001_p03", "source": "MNL-24-001", "text": "Bank 1 ignition coil primary resistance specification: 0.4 to 0.6 ohms across terminals 1 and 2."},
        {"id": "chunk_tsb_112_p01", "source": "TSB-22-112", "text": "Moisture intrusion at engine bulkhead wiring harness connector C102 causes pin resistance variance."},
        {"id": "chunk_rcl_088_p01", "source": "RCL-23-088B", "text": "Flash Battery Control Module software to version v1.0.0 or higher to resolve false thermal warnings."}
    ]

    logging.info("=" * 80)
    logging.info("SCALABLE BATCH EMBEDDING PIPELINE DEMO")
    logging.info("=" * 80)

    # RUN 1: Initial Processing (Embeds chunks or uses existing cache)
    logging.info("\n=== RUN 1: Primary Ingestion & Batch Embedding ===")
    summary1 = pipeline.process_chunks(sample_chunks, batch_size=2)

    # RUN 2: Immediate Re-run (Demonstrates Idempotent Caching - 100% Skipped, $0 Cost)
    logging.info("\n=== RUN 2: Immediate Re-run (Testing Idempotent Resumption) ===")
    summary2 = pipeline.process_chunks(sample_chunks, batch_size=2)

    logging.info("\n--- RESUMPTION VERIFICATION ---")
    if summary2["skipped_existing"] == len(sample_chunks) and summary2["embedded"] == 0:
        logging.info("✅ SUCCESS: 100%% of existing chunks skipped on re-run! $0.00 USD cost incurred.")
    else:
        logging.warning("⚠️ Caching verification failed.")

    logging.info("=" * 80)
    logging.info("DEMO COMPLETED. Output saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_batch_embedding_demo()
