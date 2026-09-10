"""
RAG Observability, Query Caching, Structured Logging & Usage Cost Tracking.

Features:
1. SHA-256 Query Cache: Caches identical question responses with TTL to avoid redundant retrieval & generation.
2. Structured JSON Logger: Emits standardized audit logs for each request with tokens, latency, sources, and cost.
3. Token & Cost Estimation: Tracks input/output token usage with per-1k pricing model ($0.00015 / 1k input, $0.00060 / 1k output).
4. Usage Reporting: Aggregates metrics (cache hit rate, total cost, average latency) for operational oversight.
"""

import os
import sys
import json
import time
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

# Setup logging
ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = ROOT_DIR / "outputs"
os.makedirs(str(OUTPUTS_DIR), exist_ok=True)

OBSERVABILITY_LOG_FILE = OUTPUTS_DIR / "rag_observability.log"
SUMMARY_REPORT_FILE = OUTPUTS_DIR / "observability_summary.json"

logger = logging.getLogger("rag_observability")
logger.setLevel(logging.INFO)

# Token counting helper
try:
    import tiktoken  # type: ignore[import-untyped, import-not-found]
    _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    _TIKTOKEN_ENCODER = None


# --- 1. SHA-256 Query Cache with TTL ---

query_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 15 * 60  # 15 minutes TTL

def cache_key(question: str, filters: Optional[Dict[str, Any]] = None) -> str:
    """Generates a deterministic SHA-256 hash key for a normalized question and filter set."""
    raw = {
        "question": question.strip().lower(),
        "filters": filters or {}
    }
    # Sort keys for deterministic serialization
    raw_str = json.dumps(raw, sort_keys=True)
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

def get_cached_answer(question: str, filters: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Retrieves cached response if key exists and has not expired."""
    key = cache_key(question, filters)
    cached = query_cache.get(key)
    if not cached:
        return None

    elapsed = time.time() - cached["created_at"]
    if elapsed > CACHE_TTL_SECONDS:
        query_cache.pop(key, None)
        return None

    # Return deep copy of response payload
    return dict(cached["response"])

def save_cached_answer(question: str, response: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> None:
    """Stores query response in cache with current timestamp."""
    key = cache_key(question, filters)
    query_cache[key] = {
        "created_at": time.time(),
        "response": response
    }

def clear_cache() -> int:
    """Clears all entries in query_cache. Returns count of purged items."""
    count = len(query_cache)
    query_cache.clear()
    return count


# --- 2. Token Counting & Cost Estimation ---

# Standard pricing model ($0.00015/1k input tokens, $0.00060/1k output tokens)
MODEL_INPUT_COST_PER_1K = 0.00015
MODEL_OUTPUT_COST_PER_1K = 0.00060

def count_tokens(text: str) -> int:
    """Counts tokens using tiktoken cl100k_base or rough char-ratio fallback."""
    if not text:
        return 0
    if _TIKTOKEN_ENCODER:
        try:
            return len(_TIKTOKEN_ENCODER.encode(text))
        except Exception:
            pass
    # Fallback: ~4 chars per token in standard English
    return max(1, len(text) // 4)

def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Calculates approximate USD cost based on input/output tokens."""
    input_cost = (input_tokens / 1000.0) * MODEL_INPUT_COST_PER_1K
    output_cost = (output_tokens / 1000.0) * MODEL_OUTPUT_COST_PER_1K
    return round(input_cost + output_cost, 6)


# --- 3. Structured Request Logging ---

# In-memory log record store for live metrics retrieval
recent_log_records: List[Dict[str, Any]] = []
MAX_RECENT_RECORDS = 500

def log_rag_request(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Emits structured JSON log entry to outputs/rag_observability.log and standard logger.
    Tracks: timestamp, request_id, question, answer_preview, sources, cache_hit, tokens, cost, latency.
    """
    entry = {
        "timestamp": record.get("timestamp") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "request_id": record.get("request_id", "req_unknown"),
        "question": record.get("question", ""),
        "answer_preview": record.get("answer", "")[:180],
        "sources": record.get("sources", []),
        "cache_hit": bool(record.get("cache_hit", False)),
        "input_tokens": int(record.get("input_tokens", 0)),
        "output_tokens": int(record.get("output_tokens", 0)),
        "total_tokens": int(record.get("input_tokens", 0)) + int(record.get("output_tokens", 0)),
        "estimated_cost": float(record.get("estimated_cost", 0.0)),
        "latency_ms": round(float(record.get("latency_ms", 0.0)), 2),
        "status": record.get("status", "answered")
    }

    # Write JSON line to file
    try:
        with open(OBSERVABILITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error("Failed to append to observability log: %s", e)

    # In-memory record list
    recent_log_records.append(entry)
    if len(recent_log_records) > MAX_RECENT_RECORDS:
        recent_log_records.pop(0)

    logger.info("RAG Request Logged: %s", json.dumps(entry))
    return entry


# --- 4. Usage Summarization & Monitoring Report ---

def load_records_from_log_file() -> List[Dict[str, Any]]:
    """Loads records from the persistent log file outputs/rag_observability.log."""
    if not OBSERVABILITY_LOG_FILE.exists():
        return []
    records = []
    try:
        with open(OBSERVABILITY_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass
    except Exception as e:
        logger.warning("Could not read observability log file: %s", e)
    return records

def summarize_usage(log_records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Summarizes usage metrics across log records:
    - total_requests
    - cache_hits & cache_hit_rate
    - total_estimated_cost
    - average_latency_ms
    - total_tokens_spent
    """
    records = log_records
    if records is None:
        records = recent_log_records if recent_log_records else load_records_from_log_file()

    total_requests = len(records)
    if total_requests == 0:
        return {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_hit_rate": 0.0,
            "total_estimated_cost": 0.0,
            "average_latency_ms": 0.0,
            "total_tokens_spent": 0,
            "active_cache_entries": len(query_cache)
        }

    cache_hits = sum(1 for item in records if item.get("cache_hit"))
    total_cost = sum(item.get("estimated_cost", 0.0) for item in records)
    total_latency = sum(item.get("latency_ms", 0.0) for item in records)
    total_tokens = sum(item.get("total_tokens", 0) for item in records)

    return {
        "total_requests": total_requests,
        "cache_hits": cache_hits,
        "cache_hit_rate": round(cache_hits / max(total_requests, 1), 2),
        "total_estimated_cost": round(total_cost, 6),
        "average_latency_ms": round(total_latency / max(total_requests, 1), 2),
        "total_tokens_spent": total_tokens,
        "active_cache_entries": len(query_cache)
    }

def generate_usage_report(output_file: Optional[str] = None) -> Dict[str, Any]:
    """Generates and writes a summary report JSON file."""
    summary = summarize_usage()
    summary["report_generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    recent = recent_log_records if recent_log_records else load_records_from_log_file()
    summary["recent_queries"] = recent[-10:]

    target_path = Path(output_file) if output_file else SUMMARY_REPORT_FILE
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
    except Exception as e:
        logger.error("Failed to write observability summary: %s", e)

    return summary
