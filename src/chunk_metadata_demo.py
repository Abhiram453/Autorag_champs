"""
Chunk Metadata & Source Tracking Demo for Autorag_champs.

Loads the automotive corpus, chunks every document with rich metadata,
demonstrates source traceback, and saves:
    - outputs/chunk_metadata_demo.log      — full demo output
    - outputs/sample_chunks_metadata.json  — all chunks with metadata for review

Run:
    python src/chunk_metadata_demo.py
"""

import os
import sys
import json
import logging
from pathlib import Path

# Ensure project root imports work when running from repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_loader import load_text  # noqa: E402
from chunk_metadata import (  # noqa: E402
    chunk_with_metadata,
    trace_chunk_to_source,
)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
os.makedirs("outputs", exist_ok=True)
LOG_FILE = os.path.join("outputs", "chunk_metadata_demo.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def _border(char="=", width=80):
    return char * width


def run_demo():
    data_dir = Path("data")
    if not data_dir.exists():
        log.error("Data directory '%s' not found.", data_dir)
        sys.exit(1)

    # Collect documents
    doc_files = sorted(
        p for p in data_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".gitkeep")
    )

    if not doc_files:
        log.error("No documents found in '%s'.", data_dir)
        sys.exit(1)

    log.info(_border())
    log.info("CHUNK METADATA & SOURCE TRACKING DEMO")
    log.info(_border())

    # --- Load and chunk every document ---
    corpus_texts = {}   # {source: full_text} for traceback verification
    all_chunks = []     # flat list of all chunks across all docs
    sample_output = {}  # structured output for JSON

    for path in doc_files:
        try:
            text = load_text(path)
        except Exception as e:
            log.warning("[SKIP] %s -- %s", path.name, e)
            continue

        source = path.name
        corpus_texts[source] = text

        chunks = chunk_with_metadata(text, source)
        all_chunks.extend(chunks)

        log.info("")
        log.info(_border("-", 70))
        log.info("Document: %s  |  Type: %s  |  %d chars  |  %d chunks",
                 source,
                 chunks[0]["doc_type"] if chunks else "?",
                 len(text),
                 len(chunks))
        log.info(_border("-", 70))

        # Print metadata for every chunk
        for c in chunks:
            log.info("")
            log.info("  [Chunk %d of %d]  ID: %s", c["chunk_index"] + 1, c["total_chunks"], c["chunk_id"])
            log.info("    source:        %s", c["source"])
            log.info("    doc_type:      %s", c["doc_type"])
            log.info("    section_title: %s", c["section_title"])
            log.info("    chunk_index:   %d", c["chunk_index"])
            log.info("    total_chunks:  %d", c["total_chunks"])
            log.info("    char_start:    %d", c["char_start"])
            log.info("    char_end:      %d", c["char_end"])
            log.info("    char_count:    %d", c["char_count"])
            log.info("    strategy:      %s", c["strategy"])
            log.info("    text_preview:  %s", repr(c["text"][:100]))

        # Build sample output (metadata + text for every chunk)
        sample_output[source] = {
            "doc_type": chunks[0]["doc_type"] if chunks else "unknown",
            "document_char_count": len(text),
            "total_chunks": len(chunks),
            "chunks": [
                {
                    "chunk_id": c["chunk_id"],
                    "source": c["source"],
                    "doc_type": c["doc_type"],
                    "section_title": c["section_title"],
                    "chunk_index": c["chunk_index"],
                    "total_chunks": c["total_chunks"],
                    "char_start": c["char_start"],
                    "char_end": c["char_end"],
                    "char_count": c["char_count"],
                    "strategy": c["strategy"],
                    "text": c["text"],
                }
                for c in chunks
            ],
        }

    # --- Consistent structure verification ---
    log.info("")
    log.info(_border())
    log.info("METADATA CONSISTENCY CHECK")
    log.info(_border())

    expected_fields = [
        "chunk_id", "source", "doc_type", "section_title",
        "chunk_index", "total_chunks", "char_start", "char_end",
        "char_count", "strategy", "text",
    ]

    all_consistent = True
    for i, chunk in enumerate(all_chunks):
        missing = [f for f in expected_fields if f not in chunk]
        if missing:
            log.error("  Chunk %d (%s) MISSING fields: %s", i, chunk.get("chunk_id", "?"), missing)
            all_consistent = False

    if all_consistent:
        log.info("  ALL %d chunks have the same %d metadata fields.", len(all_chunks), len(expected_fields))
        log.info("  Fields: %s", ", ".join(expected_fields))
    else:
        log.error("  INCONSISTENCY DETECTED in chunk metadata.")

    # --- Source traceback demonstration ---
    log.info("")
    log.info(_border())
    log.info("SOURCE TRACEBACK DEMONSTRATION")
    log.info(_border())
    log.info("")
    log.info("Simulating retrieval: a technician asks 'How do I inspect connector C102?'")
    log.info("The system retrieves the most relevant chunk. We now trace it back to its source.")
    log.info("")

    # Find the chunk that mentions "C102" (simulating a retrieval hit)
    retrieved_chunk = None
    for c in all_chunks:
        if "C102" in c["text"] and "Service Action" in c.get("section_title", ""):
            retrieved_chunk = c
            break
    # Fallback: just find any chunk mentioning C102
    if retrieved_chunk is None:
        for c in all_chunks:
            if "C102" in c["text"]:
                retrieved_chunk = c
                break

    if retrieved_chunk:
        trace = trace_chunk_to_source(retrieved_chunk, corpus_texts)

        log.info("  RETRIEVED CHUNK:")
        log.info("    chunk_id:      %s", trace["chunk_id"])
        log.info("    source:        %s", trace["source"])
        log.info("    doc_type:      %s", trace["doc_type"])
        log.info("    section_title: %s", trace["section_title"])
        log.info("    char_range:    %s", trace["char_range"])
        log.info("    position:      %s", trace["position"])
        log.info("    verified:      %s", trace["verified"])
        log.info("")
        log.info("  TRACEBACK RESULT:")
        if trace["verified"]:
            log.info("    SUCCESS -- Chunk text at offsets [%s] in '%s' matches exactly.",
                     trace["char_range"], trace["source"])
            log.info("    The answer came from section '%s' of '%s' (%s).",
                     trace["section_title"], trace["source"], trace["doc_type"])
        else:
            log.error("    MISMATCH -- Chunk could not be verified against source.")

        log.info("")
        log.info("  CITATION EXAMPLE:")
        log.info("    'According to %s, section \"%s\" (chars %s): %s'",
                 trace["source"], trace["section_title"], trace["char_range"],
                 repr(retrieved_chunk["text"][:80]))

        # Add traceback example to sample output
        sample_output["_traceback_demo"] = {
            "query": "How do I inspect connector C102?",
            "retrieved_chunk_id": trace["chunk_id"],
            "traceback": trace,
        }
    else:
        log.warning("  No chunk containing 'C102' found in corpus for traceback demo.")

    # --- Save sample chunks JSON ---
    sample_path = os.path.join("outputs", "sample_chunks_metadata.json")
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample_output, f, indent=2, ensure_ascii=False)
    log.info("")
    log.info("Sample chunks with metadata saved to %s", sample_path)

    log.info("")
    log.info(_border())
    log.info("DEMO COMPLETE. Full log saved to %s", LOG_FILE)
    log.info(_border())


if __name__ == "__main__":
    run_demo()
