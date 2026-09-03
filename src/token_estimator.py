"""
Tokenization, Context Window Budgeting, and Cost Estimation Engine for Autorag_champs.
Provides tools to count tokens using tiktoken, estimate call costs, budget RAG context windows,
and calculate corpus-scale ingestion costs for 4,000 automotive repair manuals.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Try importing tiktoken, with a fallback token estimator if tiktoken is building/installing
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

# Configure logging
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "token_cost_analysis.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

class TokenEstimator:
    def __init__(self, model_encoding="cl100k_base"):
        self.encoding_name = model_encoding
        if HAS_TIKTOKEN:
            try:
                self.encoding = tiktoken.get_encoding(model_encoding)
            except Exception:
                self.encoding = tiktoken.get_encoding("cl100k_base")
        else:
            self.encoding = None

    def count_tokens(self, text: str) -> int:
        """Counts tokens for a string of text."""
        if not text:
            return 0
        if HAS_TIKTOKEN and self.encoding:
            return len(self.encoding.encode(text))
        # Fallback heuristic: ~4 characters per token in English
        return max(1, int(len(text) / 4))

    def count_messages_tokens(self, messages: list) -> int:
        """Counts total tokens for OpenAI-style messages list (including system & user roles)."""
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += self.count_tokens(str(value))
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens

    def calculate_call_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        input_rate_per_1k: float = 0.00015,  # gpt-4o-mini rates ($0.15 / 1M input)
        output_rate_per_1k: float = 0.0006    # gpt-4o-mini rates ($0.60 / 1M output)
    ) -> float:
        """Calculates total cost in USD for a single completion call."""
        input_cost = (input_tokens / 1000.0) * input_rate_per_1k
        output_cost = (output_tokens / 1000.0) * output_rate_per_1k
        return input_cost + output_cost

    def estimate_corpus_ingestion(
        self,
        num_documents: int = 4000,
        avg_tokens_per_doc: int = 2000,
        embedding_cost_per_1k: float = 0.00002  # text-embedding-3-small ($0.02 / 1M tokens)
    ) -> dict:
        """Calculates total tokens and embedding cost for ingesting the full document corpus."""
        total_tokens = num_documents * avg_tokens_per_doc
        total_cost = (total_tokens / 1000.0) * embedding_cost_per_1k
        return {
            "num_documents": num_documents,
            "avg_tokens_per_doc": avg_tokens_per_doc,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4)
        }

    def calculate_rag_context_budget(
        self,
        system_prompt: str,
        retrieved_chunks: list,
        user_query: str,
        max_output_tokens: int = 500,
        context_limit: int = 128000
    ) -> dict:
        """Calculates token usage and context window headroom for a RAG call."""
        sys_tokens = self.count_tokens(system_prompt)
        query_tokens = self.count_tokens(user_query)
        chunks_tokens = sum(self.count_tokens(chunk) for chunk in retrieved_chunks)

        total_input_tokens = sys_tokens + query_tokens + chunks_tokens + 10 # payload overhead
        total_used = total_input_tokens + max_output_tokens
        remaining_headroom = context_limit - total_used
        utilization_pct = round((total_used / context_limit) * 100, 2)

        return {
            "system_prompt_tokens": sys_tokens,
            "user_query_tokens": query_tokens,
            "retrieved_chunks_tokens": chunks_tokens,
            "total_input_tokens": total_input_tokens,
            "max_output_tokens": max_output_tokens,
            "total_used_tokens": total_used,
            "context_limit": context_limit,
            "remaining_headroom": remaining_headroom,
            "utilization_pct": utilization_pct
        }

def run_token_analysis_demo():
    estimator = TokenEstimator()
    logging.info("=" * 80)
    logging.info("TOKENIZATION, CONTEXT LIMIT & COST ANALYSIS DEMO")
    logging.info("Encoding Engine: %s (tiktoken available: %s)", estimator.encoding_name, HAS_TIKTOKEN)
    logging.info("=" * 80)

    # 1. Single Word & String Tokenization Differences
    logging.info("\n--- 1. Token vs. Character / Word Comparison ---")
    sample_texts = [
        "refund",
        "refundable",
        "What is our refund window?",
        "Diagnostic Trouble Code P0300 (Random/Multiple Cylinder Misfire Detected)",
        "Primary Resistance Specification: 0.4 - 0.6 Ω (Ohms) Connector ID: C102"
    ]

    for text in sample_texts:
        num_tokens = estimator.count_tokens(text)
        num_words = len(text.split())
        num_chars = len(text)
        logging.info("Text: '%s'", text)
        logging.info("  -> Words: %d | Chars: %d | Tokens: %d (Avg chars/token: %.2f)",
                     num_words, num_chars, num_tokens, num_chars / num_tokens)

    # 2. Per-Call API Cost Calculation
    logging.info("\n--- 2. Single Call API Cost Calculation ---")
    sample_prompt = "Explain diagnostic step 1 for ignition coil replacement on Bank 1."
    sample_answer = "Disconnect the negative battery cable and wait 5 minutes to allow capacitors to discharge before servicing the Bank 1 ignition coil harness."
    
    in_tok = estimator.count_tokens(sample_prompt)
    out_tok = estimator.count_tokens(sample_answer)
    call_cost = estimator.calculate_call_cost(in_tok, out_tok)
    
    logging.info("Prompt Tokens: %d | Answer Tokens: %d", in_tok, out_tok)
    logging.info("Estimated Call Cost (gpt-4o-mini rates): $%f USD", call_cost)

    # 3. 4,000-Document Corpus Ingestion Cost
    logging.info("\n--- 3. Corpus Scale Cost Projection (4,000 Repair Manuals) ---")
    corpus_stats = estimator.estimate_corpus_ingestion(num_documents=4000, avg_tokens_per_doc=2000)
    logging.info("Total Documents: %d", corpus_stats["num_documents"])
    logging.info("Avg Tokens / Manual: %d", corpus_stats["avg_tokens_per_doc"])
    logging.info("Total Corpus Volume: %d tokens (%.2f Million Tokens)", 
                 corpus_stats["total_tokens"], corpus_stats["total_tokens"] / 1000000.0)
    logging.info("Total Embedding Ingestion Cost (text-embedding-3-small): $%f USD", corpus_stats["total_cost_usd"])

    # 4. RAG Context Window Budgeting (K=5 Retrieved Chunks)
    logging.info("\n--- 4. RAG Context Window Budget (K=5 Chunks) ---")
    system_prompt = "You are an expert automotive diagnostic assistant for service centers."
    retrieved_chunks = [
        "Manual Chunk 1: DTC P0300 misfire detected on multiple cylinders. Inspect fuel pressure.",
        "Manual Chunk 2: Bank 1 ignition coils specs. Primary resistance 0.4 - 0.6 ohms.",
        "Manual Chunk 3: Wiring harness connector C102 pinout diagram and corrosion bulletin.",
        "Manual Chunk 4: Battery disconnect safety protocol. Wait 5 minutes for capacitor discharge.",
        "Manual Chunk 5: Cylinder 1, 3, 5 locations on right passenger side bank."
    ]
    user_query = "What is the primary resistance spec and safety step for Bank 1 misfire?"

    budget = estimator.calculate_rag_context_budget(system_prompt, retrieved_chunks, user_query)
    logging.info("System Prompt Tokens: %d", budget["system_prompt_tokens"])
    logging.info("User Query Tokens: %d", budget["user_query_tokens"])
    logging.info("Top-5 Retrieved Chunks Tokens: %d", budget["retrieved_chunks_tokens"])
    logging.info("Total Input Payload Tokens: %d", budget["total_input_tokens"])
    logging.info("Max Response Output Buffer: %d", budget["max_output_tokens"])
    logging.info("Total Context Window Used: %d / %d tokens (%.2f%% utilization)",
                 budget["total_used_tokens"], budget["context_limit"], budget["utilization_pct"])
    logging.info("Remaining Window Headroom: %d tokens", budget["remaining_headroom"])

    logging.info("=" * 80)
    logging.info("TOKEN ANALYSIS COMPLETED. Log saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_token_analysis_demo()
