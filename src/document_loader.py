"""
Document Loading & Multi-Format Intake Engine for Autorag_champs.

Loads multiple document formats (.pdf, .txt, .md, .html) into a unified plain text form,
preserves source identity metadata for citation, handles corrupt/unreadable files gracefully,
and confirms intake with character length and preview checks.
"""

import os
import sys
import logging
from pathlib import Path

# Try importing dependencies with fallback indicators
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

# Configure logging
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "document_intake_summary.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

def load_text(path: Path) -> str:
    """
    Loads text from a single file path based on its file extension.
    Supports .pdf, .txt, .md, .html, .htm.
    """
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        if not HAS_PYPDF:
            raise ImportError("pypdf library is required to extract PDF documents.")
        reader = PdfReader(path)
        extracted_pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(extracted_pages).strip()
        if not text:
            raise ValueError("PDF contained no extractable text (scanned or image-only PDF).")
        return text

    elif suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="ignore").strip()

    elif suffix in (".html", ".htm"):
        if not HAS_BS4:
            # Fallback plain text read if bs4 is missing
            return path.read_text(encoding="utf-8", errors="ignore").strip()
        raw_html = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(raw_html, "html.parser")
        return soup.get_text(separator=" ", strip=True)

    else:
        raise ValueError(f"Unsupported file format extension: '{suffix}'")

def load_corpus(data_dir: Path) -> list:
    """
    Recursively scans data_dir for all documents, extracts plain text, tracks source metadata,
    and skips corrupt or unreadable files gracefully.
    """
    documents = []
    skipped_files = []

    if not data_dir.exists():
        logging.warning("Data directory '%s' does not exist.", data_dir)
        return documents

    logging.info("Scanning directory '%s' for documents...", data_dir)

    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue
        # Skip hidden files or placeholder files
        if path.name.startswith(".") or path.name.endswith(".gitkeep"):
            continue

        try:
            text = load_text(path)
            doc_entry = {
                "source": path.name,
                "relative_path": str(path.relative_to(data_dir.parent)),
                "extension": path.suffix.lower(),
                "text": text,
                "char_count": len(text),
                "preview": repr(text[:60])
            }
            documents.append(doc_entry)
            logging.info("  [OK] %s (%s): %d chars | Preview: %s",
                         path.name, path.suffix.lower(), len(text), doc_entry["preview"])

        except Exception as e:
            skipped_files.append({"source": path.name, "reason": str(e)})
            logging.warning("  [SKIP] %s: %e", path.name, e)

    return documents, skipped_files

def run_document_intake_demo():
    data_dir = Path("data")
    logging.info("=" * 80)
    logging.info("STARTING MULTI-FORMAT DOCUMENT INTAKE DEMO")
    logging.info("Libraries: pypdf available=%s | beautifulsoup4 available=%s", HAS_PYPDF, HAS_BS4)
    logging.info("=" * 80)

    docs, skipped = load_corpus(data_dir)

    logging.info("\n--- INTAKE SUMMARY METRICS ---")
    logging.info("Total Successfully Ingested Documents: %d", len(docs))
    logging.info("Total Skipped Files: %d", len(skipped))

    total_chars = sum(d["char_count"] for d in docs)
    logging.info("Total Corpus Character Volume: %d characters", total_chars)

    format_counts = {}
    for d in docs:
        ext = d["extension"]
        format_counts[ext] = format_counts.get(ext, 0) + 1

    logging.info("Format Breakdown: %s", format_counts)

    logging.info("\n--- INGESTED DOCUMENTS PREVIEW ---")
    for idx, doc in enumerate(docs, 1):
        logging.info("Document #%d: '%s' [%s]", idx, doc["source"], doc["extension"])
        logging.info("  Path: %s", doc["relative_path"])
        logging.info("  Character Length: %d chars", doc["char_count"])
        logging.info("  Text Preview: %s", doc["preview"])
        logging.info("-" * 40)

    logging.info("=" * 80)
    logging.info("DOCUMENT INTAKE COMPLETED. Summary saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_document_intake_demo()
