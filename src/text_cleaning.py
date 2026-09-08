import re
import unicodedata
import logging
from pathlib import Path

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.document_loader import load_corpus

def clean_text(text: str) -> str:
    """
    Cleans raw extracted text to produce consistent, retrieval-ready content.
    Task 1: Removes boilerplate (e.g., "Page X of Y", repeated headers/footers).
    Task 2: Normalizes whitespace, broken line wraps, and encoding artifacts (e.g., Unicode NFKC).
    """
    if not text:
        return text

    # Normalise encoding (Unicode NFKC)
    text = unicodedata.normalize('NFKC', text)

    # Remove boilerplate: "Page X of Y" or "Page X" alone on a line
    text = re.sub(r'(?i)^\s*Page\s+\d+(\s+of\s+\d+)?\s*$', '', text, flags=re.MULTILINE)
    # Remove boilerplate: common navigation text
    text = re.sub(r'(?i)^\s*(Back to top|Previous|Next|Table of Contents|Menu)\s*$', '', text, flags=re.MULTILINE)

    # Fix broken line wraps: Join lines if a line ends with a word character/comma and the next starts with a lowercase letter
    text = re.sub(r'([a-zA-Z,])\n([a-z])', r'\1 \2', text)

    # Normalise whitespace
    # Replace horizontal whitespace (spaces, tabs) with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Collapse 3 or more newlines into double newlines (standard paragraph break)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()

def run_cleaning_pipeline():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    data_dir = Path("data")
    
    if not data_dir.exists():
        logging.error(f"Data directory '{data_dir}' does not exist.")
        return

    docs, skipped = load_corpus(data_dir)
    
    os.makedirs("outputs", exist_ok=True)
    sample_output_path = Path("outputs/cleaning_sample_output.txt")
    
    with open(sample_output_path, "w", encoding="utf-8") as f:
        f.write("=== TEXT CLEANING PIPELINE - BEFORE & AFTER ===\n\n")
        
        for doc in docs:
            original_text = doc["text"]
            cleaned_text = clean_text(original_text)
            
            f.write(f"--- Document: {doc['source']} ---\n")
            f.write("BEFORE:\n")
            f.write(original_text[:500] + ("..." if len(original_text) > 500 else ""))
            f.write("\n\nAFTER:\n")
            f.write(cleaned_text[:500] + ("..." if len(cleaned_text) > 500 else ""))
            f.write("\n\n" + "="*80 + "\n\n")
            
            logging.info(f"Cleaned {doc['source']}: {len(original_text)} chars -> {len(cleaned_text)} chars")
            
    logging.info(f"Sample output saved to {sample_output_path}")

if __name__ == "__main__":
    run_cleaning_pipeline()
