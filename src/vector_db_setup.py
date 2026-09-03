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

def run_vector_db_setup():
    # Setup logging
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/vector_db_setup.log"
    
    logger = logging.getLogger("vector_db")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("VECTOR DATABASE SETUP & COLLECTION DESIGN")
    logger.info("=" * 80)

    if not HAS_QDRANT:
        logger.error("qdrant-client library not installed. Please run: pip install qdrant-client")
        return

    # Task 1: Set up a vector database
    # We will use a local file-based Qdrant database to show it's reachable and configured locally
    db_path = "outputs/qdrant_db"
    logger.info(f"Setting up Qdrant client at local path: {db_path}")
    client = QdrantClient(path=db_path)

    # Task 2: Create a correctly sized collection
    collection_name = "knowledge_base"
    # OpenAI's text-embedding-3-small has a dimension of 1536
    vector_dimension = 1536 
    
    logger.info(f"Creating collection '{collection_name}' with vector dimension {vector_dimension}")
    
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=vector_dimension, 
            distance=models.Distance.COSINE
        ),
    )

    # Task 3: Design the stored record schema
    # Schema implicitly uses Payload in Qdrant for metadata and text
    logger.info("Schema designed: ID (UUID or int), Vector (1536 floats), Payload (text, source, chunk_id, metadata)")

    # Task 4: Insert and read back a test record
    # Let's load the first record from embedded_corpus.json if it exists, otherwise use a dummy
    embedded_file = Path("outputs/embedded_corpus.json")
    
    test_record = None
    if embedded_file.exists():
        with open(embedded_file, "r", encoding="utf-8") as f:
            corpus = json.load(f)
            if corpus:
                test_record = corpus[0]
                logger.info("Loaded test record from outputs/embedded_corpus.json")
    
    if not test_record:
        logger.info("No embedded_corpus.json found, creating a dummy test record")
        test_record = {
            "chunk_id": "dummy_chunk_1",
            "source": "dummy_source.txt",
            "text": "This is a test document about vector databases.",
            "metadata": {"section": "intro", "page": 1},
            "embedding": [0.1] * vector_dimension
        }

    vector = test_record["embedding"]
    
    # ensure dimension matches
    if len(vector) != vector_dimension:
        logger.warning(f"Vector dimension ({len(vector)}) doesn't match configured dimension ({vector_dimension}). Adjusting...")
        if len(vector) > vector_dimension:
            vector = vector[:vector_dimension]
        else:
            vector.extend([0.0] * (vector_dimension - len(vector)))

    payload = {
        "text": test_record["text"],
        "source": test_record.get("source", "unknown"),
        "chunk_id": test_record.get("chunk_id", "unknown"),
        "metadata": test_record.get("metadata", {})
    }
    
    record_id = 1
    
    logger.info(f"Inserting test record ID={record_id} into collection '{collection_name}'...")
    
    operation_info = client.upsert(
        collection_name=collection_name,
        wait=True,
        points=[
            models.PointStruct(
                id=record_id,
                vector=vector,
                payload=payload
            )
        ]
    )
    logger.info(f"Insert status: {operation_info.status}")

    # Read back the test record
    logger.info(f"Reading back test record ID={record_id}...")
    retrieved_points = client.retrieve(
        collection_name=collection_name,
        ids=[record_id],
        with_payload=True,
        with_vectors=True
    )

    if retrieved_points:
        point = retrieved_points[0]
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION OUTPUT")
        logger.info("=" * 80)
        logger.info(f"Successfully retrieved record ID: {point.id}")
        logger.info(f"Vector length: {len(point.vector)}")
        logger.info(f"Payload Text: {point.payload.get('text')[:100]}...")
        logger.info(f"Payload Metadata: {point.payload}")
        logger.info("=" * 80)
    else:
        logger.error(f"Failed to retrieve record ID={record_id}")

if __name__ == "__main__":
    run_vector_db_setup()
