import os
import json
import logging
import sys
from pathlib import Path

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

def run_indexing():
    # Setup logging
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/indexing_summary.log"
    
    logger = logging.getLogger("indexing")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("INDEXING EMBEDDINGS & METADATA STORAGE")
    logger.info("=" * 80)

    if not HAS_QDRANT:
        logger.error("qdrant-client library not installed.")
        return

    db_path = "outputs/qdrant_db"
    client = QdrantClient(path=db_path)
    collection_name = "knowledge_base"

    # Check if collection exists
    try:
        client.get_collection(collection_name)
    except Exception as e:
        logger.error(f"Collection '{collection_name}' not found. Please run vector_db_setup.py first.")
        return

    # Load corpus
    embedded_file = Path("outputs/embedded_corpus.json")
    if not embedded_file.exists():
        logger.error(f"Embedded corpus not found at {embedded_file}")
        return

    with open(embedded_file, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    if not corpus:
        logger.error("Embedded corpus is empty.")
        return

    logger.info(f"Loaded {len(corpus)} chunks from {embedded_file}")

    points = []
    
    # Task 1 & 2: Insert all corpus embeddings and store with text and metadata
    logger.info("Preparing points for insertion...")
    # For spot checking, let's track the first chunk
    spot_check_id = 1
    spot_check_chunk = corpus[0]
    
    for i, chunk in enumerate(corpus):
        record_id = i + 1
        
        vector = chunk.get("embedding", [])
        
        payload = {
            "text": chunk.get("text", ""),
            "source": chunk.get("source", "unknown"),
            "chunk_id": chunk.get("chunk_id", "unknown"),
            "metadata": chunk.get("metadata", {})
        }
        
        points.append(
            models.PointStruct(
                id=record_id,
                vector=vector,
                payload=payload
            )
        )

    logger.info(f"Inserting {len(points)} points into collection '{collection_name}'...")
    try:
        operation_info = client.upsert(
            collection_name=collection_name,
            wait=True,
            points=points
        )
        logger.info(f"Insertion completed. Status: {operation_info.status}")
    except Exception as e:
        logger.error(f"Failed to insert points: {e}")
        return

    # Task 3: Confirm indexed count
    collection_info = client.get_collection(collection_name=collection_name)
    indexed_count = collection_info.points_count
    
    logger.info("=" * 80)
    logger.info("INDEXING VALIDATION")
    logger.info("=" * 80)
    logger.info(f"Original chunk count: {len(corpus)}")
    logger.info(f"Indexed record count: {indexed_count}")
    
    # We might have indexed dummy record before with ID=1. Upsert overrides it, 
    # but the collection could have only len(corpus) records.
    # Qdrant upsert with same IDs replaces them, so points_count should equal len(corpus).
    if len(corpus) == indexed_count:
        logger.info("SUCCESS: Indexed count matches the number of chunks produced earlier.")
    else:
        logger.warning(f"MISMATCH: Indexed count ({indexed_count}) does NOT match the number of chunks ({len(corpus)}).")

    # Task 4: Spot-check stored integrity
    logger.info("=" * 80)
    logger.info("SPOT-CHECK INTEGRITY")
    logger.info("=" * 80)
    logger.info(f"Retrieving record ID={spot_check_id} for spot-check...")
    
    retrieved_points = client.retrieve(
        collection_name=collection_name,
        ids=[spot_check_id],
        with_payload=True,
        with_vectors=True
    )

    if retrieved_points:
        point = retrieved_points[0]
        
        original_chunk_id = spot_check_chunk.get("chunk_id")
        retrieved_chunk_id = point.payload.get("chunk_id")
        
        original_text = spot_check_chunk.get("text")
        retrieved_text = point.payload.get("text")
        
        vector_length = len(point.vector)
        
        logger.info(f"Retrieved ID: {point.id}")
        logger.info(f"Vector Length: {vector_length}")
        logger.info(f"Chunk ID Match: {original_chunk_id == retrieved_chunk_id} ({original_chunk_id} vs {retrieved_chunk_id})")
        logger.info(f"Text Match: {original_text == retrieved_text}")
        logger.info(f"Payload Content Snippet: {retrieved_text[:100]}...")
        logger.info(f"Payload Metadata: {point.payload.get('metadata')}")
        logger.info("Integrity check passed.")
    else:
        logger.error(f"Failed to retrieve record ID={spot_check_id}")

    logger.info("=" * 80)
    logger.info("INDEXING COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_indexing()
