"""
Chunking Strategy Comparison Runner for Autorag_champs.

Loads the automotive corpus, applies both chunking strategies (fixed-size
with overlap and section-based), prints a detailed comparison table, and
saves:
    - outputs/chunking_comparison.log   — full comparison report
    - outputs/sample_chunks.json        — first 3 chunks per strategy per doc

Run:
    python src/chunking_comparison.py
"""

import os
import sys
import json
import logging
from pathlib import Path
from statistics import mean

# Ensure project root imports work when running from repo root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from document_loader import load_text  # noqa: E402
from chunking import chunk_fixed_size, chunk_by_section  # noqa: E402

# ---------------------------------------------------------------------------
# Logging setup — both console and file
# ---------------------------------------------------------------------------
os.makedirs("outputs", exist_ok=True)
LOG_FILE = os.path.join("outputs", "chunking_comparison.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CHUNK_SIZE = 500       # chars per fixed-size chunk
OVERLAP = 100          # overlap between consecutive fixed-size chunks
MIN_SECTION_LEN = 100  # minimum section length before merging
SAMPLE_COUNT = 3       # number of sample chunks to save per strategy per doc


def _stats(chunks):
    """Return a stats dict for a list of chunks."""
    if not chunks:
        return {"count": 0, "avg": 0, "min": 0, "max": 0}
    sizes = [c["char_count"] for c in chunks]
    return {
        "count": len(sizes),
        "avg": round(mean(sizes), 1),
        "min": min(sizes),
        "max": max(sizes),
    }


def _border(char="=", width=80):
    return char * width


def run_comparison():
    data_dir = Path("data")
    if not data_dir.exists():
        log.error("Data directory '%s' not found.", data_dir)
        sys.exit(1)

    # Collect documents (reuse load_text from document_loader)
    doc_files = sorted(
        p for p in data_dir.rglob("*")
        if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".gitkeep")
    )

    if not doc_files:
        log.error("No documents found in '%s'.", data_dir)
        sys.exit(1)

    log.info(_border())
    log.info("CHUNKING STRATEGY COMPARISON REPORT")
    log.info("Strategies: Fixed-Size (%d chars, %d overlap)  |  Section-Based (min %d chars)",
             CHUNK_SIZE, OVERLAP, MIN_SECTION_LEN)
    log.info(_border())

    all_fixed = []
    all_section = []
    sample_chunks = {}  # keyed by source

    for path in doc_files:
        try:
            text = load_text(path)
        except Exception as e:
            log.warning("[SKIP] %s — %s", path.name, e)
            continue

        source = path.name

        fixed = chunk_fixed_size(text, source, CHUNK_SIZE, OVERLAP)
        section = chunk_by_section(text, source, MIN_SECTION_LEN)

        all_fixed.extend(fixed)
        all_section.extend(section)

        fs = _stats(fixed)
        ss = _stats(section)

        log.info("")
        log.info("--- Document: %s (%d chars) ---", source, len(text))
        log.info("")
        log.info("  %-22s  %10s  %10s", "", "Fixed-Size", "Section")
        log.info("  %-22s  %10s  %10s", "-" * 22, "-" * 10, "-" * 10)
        log.info("  %-22s  %10d  %10d", "Chunk count", fs["count"], ss["count"])
        log.info("  %-22s  %10.1f  %10.1f", "Avg chunk size (chars)", fs["avg"], ss["avg"])
        log.info("  %-22s  %10d  %10d", "Min chunk size", fs["min"], ss["min"])
        log.info("  %-22s  %10d  %10d", "Max chunk size", fs["max"], ss["max"])

        # Collect sample chunks
        sample_chunks[source] = {
            "document_char_count": len(text),
            "fixed_size": [
                {
                    "chunk_index": c["chunk_index"],
                    "char_count": c["char_count"],
                    "text": c["text"],
                }
                for c in fixed[:SAMPLE_COUNT]
            ],
            "section_based": [
                {
                    "chunk_index": c["chunk_index"],
                    "char_count": c["char_count"],
                    "text": c["text"],
                }
                for c in section[:SAMPLE_COUNT]
            ],
        }

    # ── Corpus-wide summary ──────────────────────────────────────────────
    fs_total = _stats(all_fixed)
    ss_total = _stats(all_section)

    log.info("")
    log.info(_border())
    log.info("CORPUS-WIDE SUMMARY  (%d documents)", len(doc_files))
    log.info(_border())
    log.info("")
    log.info("  %-22s  %10s  %10s", "", "Fixed-Size", "Section")
    log.info("  %-22s  %10s  %10s", "-" * 22, "-" * 10, "-" * 10)
    log.info("  %-22s  %10d  %10d", "Total chunks", fs_total["count"], ss_total["count"])
    log.info("  %-22s  %10.1f  %10.1f", "Avg chunk size (chars)", fs_total["avg"], ss_total["avg"])
    log.info("  %-22s  %10d  %10d", "Min chunk size", fs_total["min"], ss_total["min"])
    log.info("  %-22s  %10d  %10d", "Max chunk size", fs_total["max"], ss_total["max"])

    # ── Justification ────────────────────────────────────────────────────
    log.info("")
    log.info(_border())
    log.info("STRATEGY JUSTIFICATION")
    log.info(_border())
    log.info("""
CHOSEN STRATEGY: Section-Based (Semantic) Chunking

Why section-based chunking is the best fit for this automotive corpus:

1. STRUCTURAL INTEGRITY
   Repair manuals, TSBs, and recall notices are organized by numbered sections
   (e.g. "1. SYSTEM OVERVIEW", "### 3. Service Action"). Splitting on these
   boundaries keeps each procedure or topic self-contained within a single chunk.

2. RETRIEVAL PRECISION
   A technician asking "How do I inspect connector C102?" should receive the
   complete "3. Service Action" section — not half of it cut off at an arbitrary
   500-character boundary. Section-based chunks preserve the full answer.

3. NATURAL SIZE DISTRIBUTION
   Automotive sections are naturally concise (typically 100–600 chars). This
   avoids the trade-off that plagues fixed-size chunking: too small splits
   mid-step, too large merges unrelated sections.

4. CONTEXT WINDOW FIT
   Chunk size must fit within the model's context window alongside the system
   prompt, user query, and other retrieved chunks. Section-based chunks are
   compact enough (~200–500 chars) to stack 3–5 retrieved chunks into a single
   prompt while leaving ample room for the model to generate its answer.

5. HOW CHUNK SIZE RELATES TO THE CONTEXT WINDOW
   The context window is the total token budget for one API call (e.g. 4K, 8K,
   128K tokens). Every retrieved chunk consumes part of that budget. If chunks
   are too large, fewer can be retrieved and the model sees less diversity of
   evidence. If chunks are too small, they lack sufficient context and the model
   struggles to synthesize a coherent answer. The ideal chunk size allows
   multiple relevant chunks plus the system prompt plus the user query to fit
   comfortably within the context window.

TRADE-OFFS: Fixed-size chunking is simpler to implement and guarantees uniform
chunk sizes, which can be advantageous for cost prediction and batch embedding.
However, it sacrifices semantic coherence — a chunk may begin mid-sentence and
end mid-paragraph, reducing retrieval quality for structured documents like ours.
""")

    # ── Save sample chunks JSON ──────────────────────────────────────────
    sample_path = os.path.join("outputs", "sample_chunks.json")
    with open(sample_path, "w", encoding="utf-8") as f:
        json.dump(sample_chunks, f, indent=2, ensure_ascii=False)
    log.info("Sample chunks saved to %s", sample_path)

    log.info(_border())
    log.info("COMPARISON COMPLETE. Report saved to %s", LOG_FILE)
    log.info(_border())


if __name__ == "__main__":
    run_comparison()
