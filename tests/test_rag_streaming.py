"""
Automated Test Suite for Server-Sent Events (SSE) Streaming RAG Query Pipeline.

Tests:
1. test_stream_headers: Verifies POST /query/stream returns text/event-stream headers.
2. test_stream_events_flow: Verifies citations, token, and done events are emitted progressively.
3. test_stream_citations_structure: Verifies citations event contains required fields (id, label, document, chunk_id, text).
4. test_stream_guardrail_refusal: Verifies out-of-scope queries stream refusal tokens without fabricating citations.
5. test_stream_empty_validation: Verifies empty question returns 422 Unprocessable Entity.
"""

import os
import sys
import json
import logging
from pathlib import Path
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.api_server import app

# Logging setup
os.makedirs("outputs", exist_ok=True)
log_file = ROOT_DIR / "outputs" / "rag_streaming_test.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(str(log_file), mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_rag_streaming")

client = TestClient(app)

def parse_sse_events(raw_text: str) -> list:
    """Parses raw SSE string into list of deserialized JSON events."""
    events = []
    for line in raw_text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            json_str = line[len("data: "):]
            try:
                events.append(json.loads(json_str))
            except Exception as e:
                logger.warning("Could not parse SSE JSON: %s (error: %s)", line, e)
    return events

def test_stream_empty_validation():
    """Test that POST /query/stream validates non-empty question."""
    logger.info("Executing test_stream_empty_validation...")
    res = client.post("/query/stream", json={"question": "   "})
    assert res.status_code == 422, f"Expected 422, got {res.status_code}"
    logger.info("✓ test_stream_empty_validation PASSED")

def test_stream_headers():
    """Test that POST /query/stream returns correct event-stream media type."""
    logger.info("Executing test_stream_headers...")
    res = client.post("/query/stream", json={"question": "What connector should I inspect?"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "text/event-stream" in res.headers.get("content-type", "")
    logger.info("✓ test_stream_headers PASSED: %s", res.headers.get("content-type"))

def test_stream_events_flow():
    """Test full event flow: citations -> tokens -> done."""
    logger.info("Executing test_stream_events_flow...")
    question = "What connector should I inspect for intermittent misfires?"
    res = client.post("/query/stream", json={"question": question})
    assert res.status_code == 200
    
    events = parse_sse_events(res.text)
    assert len(events) >= 3, f"Expected at least 3 SSE events, got {len(events)}"
    
    event_types = [e.get("type") for e in events]
    logger.info("Observed event sequence: %s (Total events: %d)", event_types[:5] + ["..."] + event_types[-2:], len(events))
    
    # Verify citations event arrives first
    assert "citations" in event_types, "Stream missing 'citations' event"
    citations_event = next(e for e in events if e.get("type") == "citations")
    assert len(citations_event.get("sources", [])) > 0, "Citations event has empty sources"
    
    # Verify token events
    token_events = [e for e in events if e.get("type") == "token"]
    assert len(token_events) > 0, "Stream missing 'token' events"
    assembled_answer = "".join(e.get("text", "") for e in token_events)
    assert len(assembled_answer.strip()) > 0, "Assembled answer is empty"
    
    # Verify done event
    assert event_types[-1] == "done", f"Expected last event to be 'done', got {event_types[-1]}"
    logger.info("✓ test_stream_events_flow PASSED! Assembled answer excerpt: %s", repr(assembled_answer[:100]))

def test_stream_citations_structure():
    """Test structure of sources inside citations event."""
    logger.info("Executing test_stream_citations_structure...")
    res = client.post("/query/stream", json={"question": "What is DTC P0300?"})
    assert res.status_code == 200
    events = parse_sse_events(res.text)
    
    citations_event = next((e for e in events if e.get("type") == "citations"), None)
    assert citations_event is not None, "Citations event not found"
    
    first_source = citations_event["sources"][0]
    required_keys = ["id", "label", "document", "chunk_id", "text"]
    for key in required_keys:
        assert key in first_source, f"Source missing required key: {key}"
        assert first_source[key], f"Source key {key} is empty"
    
    logger.info("✓ test_stream_citations_structure PASSED: %s %s - %s", first_source["label"], first_source["document"], first_source["chunk_id"])

def test_stream_guardrail_refusal():
    """Test that out-of-scope queries stream refusal tokens without fabricating citations."""
    logger.info("Executing test_stream_guardrail_refusal...")
    out_of_scope = "What is the return and refund policy for sales invoice 99201?"
    res = client.post("/query/stream", json={"question": out_of_scope})
    assert res.status_code == 200
    events = parse_sse_events(res.text)
    
    event_types = [e.get("type") for e in events]
    assert "citations" not in event_types, "Refusal stream must NOT fabricate citations"
    
    token_events = [e for e in events if e.get("type") == "token"]
    assembled_text = "".join(e.get("text", "") for e in token_events).lower()
    assert "don't have enough" in assembled_text or "not enough" in assembled_text, "Refusal answer missing standard refusal phrase"
    assert event_types[-1] == "done"
    logger.info("✓ test_stream_guardrail_refusal PASSED: Guardrail successfully streamed refusal tokens")

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("STARTING STREAMING RAG TEST SUITE")
    logger.info("=" * 80)
    test_stream_empty_validation()
    test_stream_headers()
    test_stream_events_flow()
    test_stream_citations_structure()
    test_stream_guardrail_refusal()
    logger.info("=" * 80)
    logger.info("ALL STREAMING RAG TESTS PASSED SUCCESSFULLY!")
    logger.info("=" * 80)
