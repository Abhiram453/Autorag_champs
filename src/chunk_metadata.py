"""
Chunk Metadata & Source Tracking for Autorag_champs.

Splits automotive repair documents into retrieval-sized chunks and attaches
rich, consistent metadata to every chunk so that retrieved content can be:
  - Traced back to its exact source document, section, and character position
  - Filtered by document type, section heading, or source file
  - Cited in the assistant's answers with provenance

Metadata schema (consistent across every chunk in the corpus):
    chunk_id        — unique identifier (e.g. "sample_manual.txt::section::1")
    source          — filename of the source document
    doc_type        — document category: "repair_manual", "tsb", "recall_notice"
    section_title   — heading or label of the section (e.g. "2. DIAGNOSTIC PROCEDURES")
    chunk_index     — 0-based position of this chunk within the document
    total_chunks    — total number of chunks in the source document
    char_start      — character offset where this chunk begins in the original text
    char_end        — character offset where this chunk ends in the original text
    char_count      — number of characters in the chunk text
    strategy        — chunking strategy used ("section_based")
    text            — the actual chunk content
"""

import re
import hashlib
from typing import List, Dict, Optional


# ---------------------------------------------------------------------------
# Document type classifier
# ---------------------------------------------------------------------------

def _classify_doc_type(source: str, text: str) -> str:
    """
    Infer the document category from filename patterns and content keywords.

    Returns one of: "repair_manual", "tsb", "recall_notice", "unknown"
    """
    name_lower = source.lower()
    text_lower = text[:500].lower()  # inspect only the header area

    if "tsb" in name_lower or "technical service bulletin" in text_lower:
        return "tsb"
    if "recall" in name_lower or "safety recall" in text_lower:
        return "recall_notice"
    if "manual" in name_lower or "repair manual" in text_lower or "dtc" in text_lower:
        return "repair_manual"
    return "unknown"


# ---------------------------------------------------------------------------
# Section heading extractor
# ---------------------------------------------------------------------------

_SECTION_PATTERN = re.compile(
    r"""
    (?:                         # --- Markdown headings ---
        ^[ \t]*\#{1,4}\s+(.+)  #   "# Heading" through "#### Heading" → capture title
    )
    |
    (?:                         # --- Numbered sections (plain text) ---
        ^[ \t]*(\d{1,2}\.\s+   #   "1. ", "2. " at line start
        [A-Z].*)                #   followed by uppercase title text → capture
    )
    """,
    re.MULTILINE | re.VERBOSE,
)


def _extract_section_title(text: str) -> str:
    """
    Extract the section heading from the first line(s) of a chunk's text.
    Returns the heading text or "Preamble" if no heading is found.
    """
    # Try the regex on the first line
    first_line = text.strip().split("\n")[0].strip()
    match = _SECTION_PATTERN.match(first_line)
    if match:
        # group(1) is markdown heading, group(2) is numbered section
        title = match.group(1) or match.group(2)
        if title:
            return title.strip().rstrip("*").strip()

    # Heuristic: if the first line is ALL CAPS or starts with a number, use it
    if first_line and (first_line.isupper() or re.match(r"^\d+\.\s+[A-Z]", first_line)):
        return first_line.strip()

    return "Preamble"


# ---------------------------------------------------------------------------
# Section-based splitting with position tracking
# ---------------------------------------------------------------------------

_SPLIT_PATTERN = re.compile(
    r"""
    (?:                         # --- Markdown headings ---
        ^[ \t]*\#{1,4}\s+.+    #   "# Heading" through "#### Heading"
    )
    |
    (?:                         # --- Numbered sections (plain text) ---
        ^[ \t]*\d{1,2}\.\s+    #   "1. ", "2. " at line start
        [A-Z]                   #   followed by an uppercase letter
    )
    """,
    re.MULTILINE | re.VERBOSE,
)

_MIN_SECTION_LEN = 100


def chunk_with_metadata(
    text: str,
    source: str,
    doc_type: Optional[str] = None,
    min_section_len: int = _MIN_SECTION_LEN,
) -> List[Dict]:
    """
    Split *text* on structural section boundaries and attach rich metadata
    to every chunk for source tracking and citation.

    Parameters
    ----------
    text : str
        Full plain-text content of one document.
    source : str
        Filename used as the source identifier.
    doc_type : str or None
        Document category override. Auto-detected if None.
    min_section_len : int
        Minimum characters for a standalone chunk (default 100).

    Returns
    -------
    list[dict]
        Each dict has the full metadata schema described in the module docstring.
    """
    if not text or not text.strip():
        return []

    if doc_type is None:
        doc_type = _classify_doc_type(source, text)

    # --- Split into raw sections with position tracking ---
    matches = list(_SPLIT_PATTERN.finditer(text))

    raw_sections: List[Dict] = []  # {"text": ..., "start": ..., "end": ...}

    if matches:
        positions = [m.start() for m in matches]

        # Preamble: text before the first heading
        if positions[0] > 0:
            raw_sections.append({
                "text": text[:positions[0]],
                "start": 0,
                "end": positions[0],
            })

        for i, pos in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(text)
            raw_sections.append({
                "text": text[pos:end],
                "start": pos,
                "end": end,
            })
    else:
        # Fallback: split on double newlines (paragraph boundaries)
        parts = re.split(r"\n\s*\n", text)
        offset = 0
        for part in parts:
            idx = text.find(part, offset)
            raw_sections.append({
                "text": part,
                "start": idx,
                "end": idx + len(part),
            })
            offset = idx + len(part)

    # --- Merge tiny sections into their predecessor ---
    merged: List[Dict] = []
    for section in raw_sections:
        stripped = section["text"].strip()
        if not stripped:
            continue
        if merged and len(stripped) < min_section_len:
            merged[-1]["text"] += "\n\n" + stripped
            merged[-1]["end"] = section["end"]
        else:
            merged.append({
                "text": stripped,
                "start": section["start"],
                "end": section["end"],
            })

    total_chunks = len(merged)

    # --- Build chunk dicts with full metadata ---
    chunks: List[Dict] = []
    for idx, section in enumerate(merged):
        section_title = _extract_section_title(section["text"])
        chunk_id = f"{source}::section::{idx}"

        chunks.append({
            "chunk_id": chunk_id,
            "source": source,
            "doc_type": doc_type,
            "section_title": section_title,
            "chunk_index": idx,
            "total_chunks": total_chunks,
            "char_start": section["start"],
            "char_end": section["end"],
            "char_count": len(section["text"]),
            "strategy": "section_based",
            "text": section["text"],
        })

    return chunks


# ---------------------------------------------------------------------------
# Corpus-level chunking
# ---------------------------------------------------------------------------

def chunk_corpus_with_metadata(documents: List[Dict]) -> List[Dict]:
    """
    Apply section-based chunking with metadata to every document.

    Parameters
    ----------
    documents : list[dict]
        Output of ``document_loader.load_corpus`` — each dict must have
        ``text`` and ``source`` keys.

    Returns
    -------
    list[dict]
        Flat list of all chunks across all documents, each with full metadata.
    """
    all_chunks: List[Dict] = []

    for doc in documents:
        text = doc["text"]
        source = doc["source"]
        doc_type = doc.get("doc_type")  # allow pre-classified docs

        chunks = chunk_with_metadata(text, source, doc_type)
        all_chunks.extend(chunks)

    return all_chunks


# ---------------------------------------------------------------------------
# Traceback: given a chunk, recover its exact origin
# ---------------------------------------------------------------------------

def trace_chunk_to_source(chunk: Dict, corpus_texts: Dict[str, str]) -> Dict:
    """
    Demonstrate that a chunk can be traced back to its exact source.

    Given a chunk dict and a mapping of {source_filename: full_text},
    verify that the chunk text appears at the recorded character offsets
    in the original document.

    Returns
    -------
    dict with keys:
        source           — filename
        doc_type         — document category
        section_title    — section heading
        char_range       — "start-end" character range
        position         — "chunk X of Y"
        verified         — True if text at recorded offsets matches chunk text
        original_snippet — the text extracted from the source at recorded offsets
    """
    source = chunk["source"]
    original_text = corpus_texts.get(source, "")

    # Extract text from original at the recorded offsets
    extracted = original_text[chunk["char_start"]:chunk["char_end"]].strip()
    chunk_text_stripped = chunk["text"].strip()

    return {
        "chunk_id": chunk["chunk_id"],
        "source": source,
        "doc_type": chunk["doc_type"],
        "section_title": chunk["section_title"],
        "char_range": f"{chunk['char_start']}-{chunk['char_end']}",
        "position": f"chunk {chunk['chunk_index'] + 1} of {chunk['total_chunks']}",
        "verified": extracted == chunk_text_stripped,
        "original_snippet": extracted[:120] + ("..." if len(extracted) > 120 else ""),
    }
