"""
Unit and Integration Test Suite for RAG Observability, Query Caching, Structured Logging & Cost Tracking.

Tests:
1. Cache key determinism, case-insensitivity, and normalization.
2. In-memory cache hit, miss, and TTL expiration logic.
3. Token counting and cost calculation accuracy.
4. Structured logging output schema in outputs/rag_observability.log.
5. Metrics aggregation (cache hit rate, total cost, latency).
6. API endpoint integration (/query caching, /metrics/observability, /cache/clear).
"""

import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure workspace root is in python path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.observability import (
    cache_key,
    get_cached_answer,
    save_cached_answer,
    clear_cache,
    count_tokens,
    estimate_cost,
    log_rag_request,
    summarize_usage,
    generate_usage_report,
    OBSERVABILITY_LOG_FILE,
    query_cache,
)
from src.api_server import app, rag_engine

client = TestClient(app)

def test_cache_key_determinism():
    """Verifies that cache keys are deterministic, case-insensitive, and whitespace invariant."""
    k1 = cache_key("What is DTC P0300?")
    k2 = cache_key("   what is dtc p0300?   ")
    k3 = cache_key("What is DTC P0300?", filters={"k": 4})
    k4 = cache_key("what is dtc p0300?", filters={"k": 4})
    k_diff = cache_key("What is DTC P0301?")

    assert k1 == k2, "Cache key must normalize casing and whitespace"
    assert k3 == k4, "Cache key with identical filters must match"
    assert k1 != k_diff, "Different questions must yield different cache keys"
    assert len(k1) == 64, "Key should be 64-char hex SHA-256"
    print("PASS: test_cache_key_determinism")

def test_cache_lifecycle_and_ttl():
    """Tests save, retrieval, cache clear, and TTL expiration."""
    clear_cache()
    assert len(query_cache) == 0

    q = "What is the primary resistance for Bank 1 coils?"
    cached = get_cached_answer(q)
    assert cached is None, "Empty cache should return None"

    sample_resp = {
        "question": q,
        "answer": "Primary resistance is 0.4 to 0.6 ohms.",
        "sources": [{"source": "sample_manual.txt"}],
        "status": "answered"
    }
    save_cached_answer(q, sample_resp)

    # Cache hit
    retrieved = get_cached_answer(q)
    assert retrieved is not None
    assert retrieved["answer"] == sample_resp["answer"]

    # Test TTL expiration by simulating time passing
    key = cache_key(q)
    query_cache[key]["created_at"] = time.time() - (16 * 60)  # 16 minutes ago (> 15m TTL)
    expired = get_cached_answer(q)
    assert expired is None, "Expired cache item should return None and be pruned"

    # Test clear_cache
    save_cached_answer("query 1", {"answer": "a1"})
    save_cached_answer("query 2", {"answer": "a2"})
    purged = clear_cache()
    assert purged == 2
    assert len(query_cache) == 0
    print("PASS: test_cache_lifecycle_and_ttl")

def test_token_counting_and_cost_estimation():
    """Verifies token estimation and standard pricing calculation."""
    sample_text = "DTC P0300 indicates random misfire across multiple engine cylinders."
    tokens = count_tokens(sample_text)
    assert tokens > 0, "Token count should be positive"

    # Pricing formula: (input / 1000) * 0.00015 + (output / 1000) * 0.00060
    cost = estimate_cost(input_tokens=1000, output_tokens=1000)
    expected = 0.00015 + 0.00060
    assert abs(cost - expected) < 1e-6, f"Expected {expected}, got {cost}"

    cost_zero = estimate_cost(0, 0)
    assert cost_zero == 0.0
    print("PASS: test_token_counting_and_cost_estimation")

def test_structured_logging():
    """Verifies that requests are logged as structured JSON entries."""
    if OBSERVABILITY_LOG_FILE.exists():
        initial_lines = len(OBSERVABILITY_LOG_FILE.read_text(encoding="utf-8").strip().splitlines())
    else:
        initial_lines = 0

    record = {
        "request_id": "req_test_99",
        "question": "Testing structured logger",
        "answer": "This is a test answer for log verification.",
        "sources": ["test_doc.md"],
        "cache_hit": False,
        "input_tokens": 120,
        "output_tokens": 40,
        "estimated_cost": 0.000042,
        "latency_ms": 35.5,
        "status": "answered"
    }
    entry = log_rag_request(record)

    assert entry["request_id"] == "req_test_99"
    assert entry["total_tokens"] == 160
    assert entry["cache_hit"] is False

    # Check file exists and has new line
    assert OBSERVABILITY_LOG_FILE.exists()
    lines = OBSERVABILITY_LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= initial_lines + 1
    last_line = json.loads(lines[-1])
    assert last_line["request_id"] == "req_test_99"
    assert "timestamp" in last_line
    print("PASS: test_structured_logging")

def test_usage_summarization_and_report():
    """Tests aggregation of metrics across log records."""
    dummy_records = [
        {"cache_hit": False, "total_tokens": 200, "estimated_cost": 0.0002, "latency_ms": 300.0},
        {"cache_hit": True, "total_tokens": 0, "estimated_cost": 0.0, "latency_ms": 2.0},
        {"cache_hit": True, "total_tokens": 0, "estimated_cost": 0.0, "latency_ms": 3.0},
        {"cache_hit": False, "total_tokens": 300, "estimated_cost": 0.0003, "latency_ms": 400.0},
    ]

    summary = summarize_usage(dummy_records)
    assert summary["total_requests"] == 4
    assert summary["cache_hits"] == 2
    assert summary["cache_hit_rate"] == 0.50
    assert summary["total_tokens_spent"] == 500
    assert summary["total_estimated_cost"] == 0.0005
    assert abs(summary["average_latency_ms"] - 176.25) < 0.1

    # Test report generation
    report = generate_usage_report()
    assert "total_requests" in report
    assert "report_generated_at" in report
    print("PASS: test_usage_summarization_and_report")

def test_api_query_caching_and_metrics():
    """Integration test: First query is cache miss, second query is cache hit."""
    clear_cache()

    test_q = "What is the primary resistance specification for Bank 1 coils?"

    mock_rag_response = {
        "question": test_q,
        "rewritten_query": test_q,
        "answer": "Primary resistance specification is 0.4 to 0.6 ohms across terminals 1 and 2.",
        "sources": [
            {
                "source": "sample_manual.txt",
                "chunk_id": "chunk_mnl_001",
                "section": "Ignition Diagnostics",
                "doc_type": "Repair Manual",
                "score": 0.895,
                "text": "Inspect Bank 1 ignition coils. Primary resistance specification: 0.4 to 0.6 ohms."
            }
        ],
        "citations": {},
        "top_score": 0.895,
        "confidence": 0.895,
        "status": "answered"
    }

    with patch.object(rag_engine, "query", return_value=mock_rag_response) as mock_query:
        # 1. First Call: Cache Miss
        res1 = client.post("/query", json={"question": test_q, "k": 4})
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["cache_hit"] is False
        assert "usage" in data1
        assert data1["usage"]["cache_hit"] is False
        assert data1["usage"]["input_tokens"] > 0
        assert data1["usage"]["output_tokens"] > 0
        assert data1["usage"]["estimated_cost"] > 0
        assert mock_query.call_count == 1

        # 2. Second Call: Cache Hit (Underlying RAG engine should NOT be called again)
        res2 = client.post("/query", json={"question": test_q, "k": 4})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["cache_hit"] is True
        assert data2["usage"]["cache_hit"] is True
        assert data2["usage"]["total_tokens"] == 0
        assert data2["usage"]["estimated_cost"] == 0.0
        assert data2["usage"]["latency_ms"] < 25.0  # Ultra-fast from memory cache
        assert mock_query.call_count == 1  # Still 1! Not called!

        # Answers and sources should match
        assert data1["answer"] == data2["answer"]
        assert len(data1["sources"]) == len(data2["sources"])

        # 3. GET /metrics/observability
        metrics_res = client.get("/metrics/observability")
        assert metrics_res.status_code == 200
        metrics = metrics_res.json()
        assert metrics["total_requests"] >= 2
        assert metrics["cache_hits"] >= 1
        assert metrics["active_cache_entries"] >= 1

        # 4. POST /cache/clear
        clear_res = client.post("/cache/clear")
        assert clear_res.status_code == 200
        clear_data = clear_res.json()
        assert clear_data["status"] == "cleared"
        assert clear_data["purged_entries"] >= 1

        # 5. Third Call: Should be Cache Miss again
        res3 = client.post("/query", json={"question": test_q, "k": 4})
        assert res3.status_code == 200
        data3 = res3.json()
        assert data3["cache_hit"] is False
        assert mock_query.call_count == 2  # Called again after cache purge!
        print("PASS: test_api_query_caching_and_metrics")


if __name__ == "__main__":
    print("\n--- Running RAG Observability & Query Caching Test Suite ---")
    test_cache_key_determinism()
    test_cache_lifecycle_and_ttl()
    test_token_counting_and_cost_estimation()
    test_structured_logging()
    test_usage_summarization_and_report()
    test_api_query_caching_and_metrics()
    print("\n[SUCCESS] ALL 6 TEST CASES PASSED SUCCESSFULLY!\n")
