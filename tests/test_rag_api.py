"""
Automated Test Suite for Aura Automotive RAG API & Query Endpoints.

Tests:
1. test_health_endpoint: Verifies GET /health returns 200 OK.
2. test_status_endpoint: Verifies GET /status returns valid corpus and model metadata.
3. test_query_answerable: Verifies POST /query returns grounded answer, structured sources, and chunk_ids.
4. test_query_guardrail_refusal: Verifies POST /query safely refuses out-of-scope queries (status: refused_weak_context).
5. test_query_empty_validation: Verifies POST /query returns 422 for blank queries.
6. test_frontend_serving: Verifies GET / serves the interactive HTML interface.
"""

import os
import sys
import pytest
import logging
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.api_server import app

# Setup logging
os.makedirs("outputs", exist_ok=True)
log_file = ROOT_DIR / "outputs" / "rag_api_test.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(log_file), mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_rag_api")

client = TestClient(app)

def test_health_endpoint():
    """Test GET /health liveness probe."""
    logger.info("Executing test_health_endpoint...")
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "ok"
    logger.info("✓ test_health_endpoint PASSED: %s", data)

def test_status_endpoint():
    """Test GET /status system metadata endpoint."""
    logger.info("Executing test_status_endpoint...")
    res = client.get("/status")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "operational"
    assert data["indexed_documents"] >= 1
    assert data["indexed_chunks"] >= 3
    assert data["min_top_score"] > 0
    assert len(data["corpus_sources"]) >= 1
    logger.info("✓ test_status_endpoint PASSED: %d chunks indexed", data["indexed_chunks"])

def test_frontend_serving():
    """Test GET / serves frontend HTML."""
    logger.info("Executing test_frontend_serving...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "Aura Automotive" in res.text
    assert "id=\"hub-query-input\"" in res.text
    assert "id=\"hub-query-submit\"" in res.text
    logger.info("✓ test_frontend_serving PASSED")

def test_query_empty_validation():
    """Test POST /query validation on empty string."""
    logger.info("Executing test_query_empty_validation...")
    res = client.post("/query", json={"question": "   "})
    assert res.status_code == 422, f"Expected 422 Unprocessable Entity, got {res.status_code}"
    logger.info("✓ test_query_empty_validation PASSED: 422 correctly returned")

def test_query_answerable():
    """Test POST /query with valid automotive question."""
    logger.info("Executing test_query_answerable...")
    query = "What connector should I inspect for misfire issues?"
    res = client.post("/query", json={"question": query})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    
    assert "answer" in data, "Response missing 'answer' field"
    assert "sources" in data, "Response missing 'sources' field"
    assert "top_score" in data, "Response missing 'top_score' field"
    assert "status" in data, "Response missing 'status' field"
    assert data["status"] == "answered", f"Expected answered status, got {data['status']}"
    assert len(data["sources"]) > 0, "Expected non-empty sources list"
    
    # Check source item structure
    first_src = data["sources"][0]
    assert "source" in first_src, "Source missing 'source' property"
    assert "chunk_id" in first_src, "Source missing 'chunk_id' property"
    logger.info("✓ test_query_answerable PASSED: Top Score: %.4f | Sources: %d", data["top_score"], len(data["sources"]))
    logger.info("  Sample Answer Excerpt: %s", data["answer"][:120])

def test_query_guardrail_refusal():
    """Test POST /query with out-of-scope query triggering guardrail refusal."""
    logger.info("Executing test_query_guardrail_refusal...")
    out_of_scope_query = "What is the return and refund policy for sales invoice 99201?"
    res = client.post("/query", json={"question": out_of_scope_query})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    
    assert data["status"] == "refused_weak_context", f"Expected refused_weak_context, got {data['status']}"
    assert data["sources"] == [], "Refusal response must have empty sources"
    assert "don't have enough" in data["answer"].lower() or "not enough" in data["answer"].lower()
    logger.info("✓ test_query_guardrail_refusal PASSED: Guardrail successfully prevented hallucination (Top Score: %.4f)", data["top_score"])

def test_metrics_endpoint():
    """Test GET /metrics operational metrics endpoint for Manager Command Center."""
    logger.info("Executing test_metrics_endpoint...")
    res = client.get("/metrics")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "repairs_completed" in data
    assert "open_recalls_pct" in data
    assert "pending_approvals" in data
    assert len(data["recent_activities"]) >= 1
    logger.info("✓ test_metrics_endpoint PASSED: %d repairs completed, %d%% recalls", data["repairs_completed"], data["open_recalls_pct"])

def test_audit_logs_endpoint():
    """Test GET /audit-logs compliance logs endpoint for Admin Audit Panel."""
    logger.info("Executing test_audit_logs_endpoint...")
    res = client.get("/audit-logs")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "pending_reviews" in data
    assert "audit_logs" in data
    assert len(data["pending_reviews"]) >= 1
    assert len(data["audit_logs"]) >= 1
    logger.info("✓ test_audit_logs_endpoint PASSED: %d pending reviews, %d audit entries", len(data["pending_reviews"]), len(data["audit_logs"]))

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("STARTING RAG API AUTOMATED TEST SUITE")
    logger.info("=" * 80)
    test_health_endpoint()
    test_status_endpoint()
    test_metrics_endpoint()
    test_audit_logs_endpoint()
    test_frontend_serving()
    test_query_empty_validation()
    test_query_answerable()
    test_query_guardrail_refusal()
    logger.info("=" * 80)
    logger.info("ALL RAG API TESTS COMPLETED SUCCESSFULLY!")
    logger.info("=" * 80)
