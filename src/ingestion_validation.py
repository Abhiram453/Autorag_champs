import os
import sys
import logging
import json
from pathlib import Path

# Add src to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.document_loader import load_corpus
from src.text_cleaning import clean_text
from src.chunk_metadata import chunk_corpus_with_metadata

def count_files_in_dir(data_dir: Path) -> int:
    """Count total files in directory, ignoring hidden files and .gitkeep"""
    count = 0
    for path in data_dir.rglob("*"):
        if path.is_file() and not path.name.startswith(".") and not path.name.endswith(".gitkeep"):
            count += 1
    return count

def run_ingestion_validation():
    # Setup logging to both console and file
    os.makedirs("outputs", exist_ok=True)
    log_file_path = os.path.join("outputs", "ingestion_summary.log")
    
    # We use a custom logger to prevent interfering with document_loader's basicConfig if any
    logger = logging.getLogger("ingestion")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("STARTING CORPUS PREPARATION & INGESTION VALIDATION")
    logger.info("=" * 80)

    data_dir = Path("data")
    if not data_dir.exists():
        logger.error(f"Data directory '{data_dir}' does not exist.")
        return

    # Task 1 & Task 3: Load corpus and count files
    total_files = count_files_in_dir(data_dir)
    logger.info(f"Task 3 Check: Total physical files in {data_dir} = {total_files}")

    docs, skipped = load_corpus(data_dir)
    
    # Clean text for each document
    for doc in docs:
        original_len = len(doc["text"])
        doc["text"] = clean_text(doc["text"])
        logger.info(f"Cleaned {doc['source']}: {original_len} -> {len(doc['text'])} chars")

    # Chunk with metadata
    chunks = chunk_corpus_with_metadata(docs)

    # Task 2: Report ingestion summary
    logger.info("\n" + "=" * 80)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total Source Documents (Physical): {total_files}")
    logger.info(f"Successfully Ingested Documents:   {len(docs)}")
    logger.info(f"Failed/Skipped Documents:          {len(skipped)}")
    logger.info(f"Total Chunks Created:              {len(chunks)}")
    
    if skipped:
        logger.info("\nSkipped Files Details:")
        for skip in skipped:
            logger.info(f" - {skip['source']}: {skip['reason']}")

    # Task 3: Validate completeness
    logger.info("\n" + "=" * 80)
    logger.info("COMPLETENESS VALIDATION")
    logger.info("=" * 80)
    processed_total = len(docs) + len(skipped)
    
    if processed_total == total_files:
        logger.info(f"[PASS] Completeness validation passed: {processed_total} processed == {total_files} physical files.")
    else:
        logger.error(f"[FAIL] Completeness mismatch! Processed {processed_total}, but found {total_files} physical files.")

    # Task 4: Inspect sample chunks
    logger.info("\n" + "=" * 80)
    logger.info("SAMPLE CHUNKS INSPECTION")
    logger.info("=" * 80)
    
    # Print the first two chunks as samples
    for i, chunk in enumerate(chunks[:2]):
        logger.info(f"\n--- Sample Chunk {i+1} ---")
        logger.info(f"Chunk ID:      {chunk['chunk_id']}")
        logger.info(f"Source:        {chunk['source']}")
        logger.info(f"Doc Type:      {chunk['doc_type']}")
        logger.info(f"Section Title: {chunk['section_title']}")
        logger.info(f"Position:      Chunk {chunk['chunk_index']} of {chunk['total_chunks']}")
        logger.info(f"Length:        {chunk['char_count']} characters")
        
        preview = chunk['text'].replace('\n', ' ')
        if len(preview) > 150:
            preview = preview[:150] + "..."
        logger.info(f"Preview:       {preview}")
        logger.info("-" * 40)
        
    logger.info(f"\nPipeline run completed. Summary saved to {log_file_path}")

if __name__ == "__main__":
    run_ingestion_validation()
