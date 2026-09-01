"""
Document Chunking Strategies for Autorag_champs.

Implements two chunking strategies for splitting automotive repair documents
into retrieval-sized units for a RAG pipeline:

1. Fixed-Size with Overlap  — character-based windowed splits
2. Section-Based (Semantic)  — splits on structural headers/numbered sections

Each strategy produces chunk dicts with: text, source, strategy, chunk_index, char_count.
"""

import re
from typing import List, Dict


# ---------------------------------------------------------------------------
# Strategy 1: Fixed-Size with Overlap
# ---------------------------------------------------------------------------

def chunk_fixed_size(
    text: str,
    source: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> List[Dict]:
    """
    Split *text* into chunks of *chunk_size* characters with *overlap* characters
    shared between consecutive chunks.

    Why overlap?  Without it, a retrieval query whose answer straddles two chunks
    would get only a partial answer.  The overlap creates a "safety margin" at
    chunk boundaries so context is not lost.

    Parameters
    ----------
    text : str
        The full plain-text content of one document.
    source : str
        Filename or path used for provenance tracking.
    chunk_size : int
        Maximum characters per chunk (default 500).
    overlap : int
        Characters repeated between consecutive chunks (default 100).

    Returns
    -------
    list[dict]
        Each dict: {text, source, strategy, chunk_index, char_count}
    """
    if not text or not text.strip():
        return []

    chunks: List[Dict] = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        # Only add non-empty chunks
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "source": source,
                "strategy": "fixed_size",
                "chunk_index": idx,
                "char_count": len(chunk_text),
            })
            idx += 1

        # Advance the window; if overlap >= chunk_size we'd loop forever
        step = max(chunk_size - overlap, 1)
        start += step

    return chunks


# ---------------------------------------------------------------------------
# Strategy 2: Section-Based (Semantic / Structural)
# ---------------------------------------------------------------------------

# Patterns that mark section starts in the automotive corpus:
#   - Markdown headings:        "# Title", "## Title", "### 1. Condition"
#   - Numbered plain-text:      "1. SYSTEM OVERVIEW", "2. DIAGNOSTIC PROCEDURES"
#   - HTML-style headings:      already stripped by document_loader → plain text
_SECTION_PATTERN = re.compile(
    r"""
    (?:                         # --- Markdown headings ---
        ^[ \t]*\#{1,4}\s+.+    #   "# Heading" through "#### Heading"
    )
    |
    (?:                         # --- Numbered sections (plain text) ---
        ^[ \t]*\d{1,2}\.\s+    #   "1. ", "2. ", "10. " at line start
        [A-Z]                   #   followed by an uppercase letter (title case)
    )
    """,
    re.MULTILINE | re.VERBOSE,
)

# Minimum characters for a section to be kept as its own chunk.
# Shorter fragments are merged into the previous chunk.
_MIN_SECTION_LEN = 100


def chunk_by_section(
    text: str,
    source: str,
    min_section_len: int = _MIN_SECTION_LEN,
) -> List[Dict]:
    """
    Split *text* on structural section boundaries that appear naturally in
    automotive repair manuals, TSBs, and recall notices.

    The regex detects Markdown headings (``# …``, ``### …``) and numbered
    plain-text sections (``1. SYSTEM OVERVIEW``).  Text before the first
    detected heading becomes the "preamble" chunk (metadata, title block).

    Sections shorter than *min_section_len* are merged into the preceding chunk
    to avoid tiny, low-value fragments.

    Falls back to paragraph splitting (double newline) if no section markers
    are found.

    Parameters
    ----------
    text : str
        The full plain-text content of one document.
    source : str
        Filename or path used for provenance tracking.
    min_section_len : int
        Minimum characters for a standalone chunk (default 100).

    Returns
    -------
    list[dict]
        Each dict: {text, source, strategy, chunk_index, char_count}
    """
    if not text or not text.strip():
        return []

    # Find all section-start positions
    matches = list(_SECTION_PATTERN.finditer(text))

    if matches:
        # Build raw sections from match positions
        raw_sections: List[str] = []
        positions = [m.start() for m in matches]

        # Preamble: text before the first heading
        if positions[0] > 0:
            raw_sections.append(text[: positions[0]])

        for i, pos in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            raw_sections.append(text[pos:end])
    else:
        # Fallback: split on double newlines (paragraph boundaries)
        raw_sections = re.split(r"\n\s*\n", text)

    # Merge tiny sections into their predecessor
    merged: List[str] = []
    for section in raw_sections:
        section = section.strip()
        if not section:
            continue
        if merged and len(section) < min_section_len:
            merged[-1] += "\n\n" + section
        else:
            merged.append(section)

    # Build chunk dicts
    chunks: List[Dict] = []
    for idx, section_text in enumerate(merged):
        chunks.append({
            "text": section_text,
            "source": source,
            "strategy": "section_based",
            "chunk_index": idx,
            "char_count": len(section_text),
        })

    return chunks


# ---------------------------------------------------------------------------
# Convenience: run both strategies on a loaded corpus
# ---------------------------------------------------------------------------

def chunk_corpus(
    documents: List[Dict],
    chunk_size: int = 500,
    overlap: int = 100,
    min_section_len: int = _MIN_SECTION_LEN,
) -> Dict[str, List[Dict]]:
    """
    Apply both chunking strategies to every document in *documents*.

    Parameters
    ----------
    documents : list[dict]
        Output of ``document_loader.load_corpus`` — each dict must have
        ``text`` and ``source`` keys.

    Returns
    -------
    dict with keys ``"fixed_size"`` and ``"section_based"``, each mapping
    to the flat list of all chunks produced by that strategy across all docs.
    """
    fixed_all: List[Dict] = []
    section_all: List[Dict] = []

    for doc in documents:
        text = doc["text"]
        source = doc["source"]

        fixed_all.extend(chunk_fixed_size(text, source, chunk_size, overlap))
        section_all.extend(chunk_by_section(text, source, min_section_len))

    return {
        "fixed_size": fixed_all,
        "section_based": section_all,
    }
