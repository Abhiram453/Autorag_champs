import os
import sys
import json
import math
import logging
from pathlib import Path
from dotenv import load_dotenv

try:
    from openai import OpenAI, OpenAIError
except ImportError:
    pass

def cosine_similarity(v1, v2):
    """
    Computes cosine similarity between two vectors.
    Measures the cosine of the angle between them, representing
    how similar their directions (meanings) are, regardless of magnitude.
    """
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 * mag2 == 0: return 0
    return dot / (mag1 * mag2)

def run_similarity_ranking():
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/similarity_ranking.log"
    
    logger = logging.getLogger("similarity_ranking")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("EMBEDDING SIMILARITY & DISTANCE METRICS")
    logger.info("=" * 80)

    corpus_file = Path("outputs/embedded_corpus.json")
    if not corpus_file.exists():
        logger.error(f"Embedded corpus not found at {corpus_file}. Please run api_embedding.py first.")
        return

    with open(corpus_file, "r", encoding="utf-8") as f:
        embedded_corpus = json.load(f)

    logger.info(f"Loaded {len(embedded_corpus)} embedded chunks from corpus.")

    # Task 2: Create or reuse a query embedding
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY", "mock-key")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    query_text = "What information is available regarding safety recalls and mandatory inspections?"
    
    logger.info(f"\nQuery Text: '{query_text}'")
    logger.info("Generating query embedding via API...")
    
    query_vector = []
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.embeddings.create(
            input=query_text,
            model=model_name
        )
        query_vector = response.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        return

    # Task 1: Compute similarity metric
    logger.info("\nComputing Cosine Similarity for all chunks...")
    
    scored_chunks = []
    for chunk in embedded_corpus:
        chunk_vector = chunk["embedding"]
        score = cosine_similarity(query_vector, chunk_vector)
        
        scored_chunks.append({
            "score": score,
            "chunk_id": chunk["chunk_id"],
            "source": chunk["source"],
            "section_title": chunk["section_title"],
            "text_preview": chunk["text"][:100].replace("\n", " ") + "..."
        })

    # Task 3: Rank and show results
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)

    logger.info("\n" + "=" * 80)
    logger.info("RANKED RESULTS (Most to Least Similar)")
    logger.info("=" * 80)
    
    for rank, item in enumerate(scored_chunks, 1):
        logger.info(f"Rank {rank} | Score: {item['score']:.4f}")
        logger.info(f"  Chunk ID: {item['chunk_id']} (Source: {item['source']})")
        logger.info(f"  Section:  {item['section_title']}")
        logger.info(f"  Preview:  '{item['text_preview']}'\n")

    logger.info("-" * 80)
    most_similar = scored_chunks[0]
    least_similar = scored_chunks[-1]
    
    logger.info("ANALYSIS:")
    logger.info(f"MOST SIMILAR: {most_similar['chunk_id']} (Score: {most_similar['score']:.4f})")
    logger.info(f"LEAST SIMILAR: {least_similar['chunk_id']} (Score: {least_similar['score']:.4f})")

    # Task 4: Justify the metric
    logger.info("\n" + "=" * 80)
    logger.info("METRIC JUSTIFICATION (Cosine Similarity)")
    logger.info("=" * 80)
    justification = (
        "We chose Cosine Similarity because it measures the angle between two vectors in high-dimensional space, "
        "focusing purely on the 'direction' of the meaning rather than the 'magnitude' (which can be skewed by "
        "the length of the original text or word frequencies). A score closer to 1 means the vectors point in the "
        "same semantic direction (highly similar), while a score near 0 means they are orthogonal (unrelated). "
        "This is the standard and most robust metric for comparing text embeddings."
    )
    logger.info(justification)
    logger.info("=" * 80)

if __name__ == "__main__":
    run_similarity_ranking()
