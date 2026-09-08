import os
import sys
import logging
from dotenv import load_dotenv

try:
    from openai import OpenAI, OpenAIError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from qdrant_client import QdrantClient
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

def run_similarity_search():
    # Setup logging
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/similarity_search_results.log"
    
    logger = logging.getLogger("similarity_search")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("SIMILARITY SEARCH & TOP-K RETRIEVAL")
    logger.info("=" * 80)

    if not HAS_OPENAI or not HAS_QDRANT:
        logger.error("Missing required libraries. Ensure 'openai' and 'qdrant-client' are installed.")
        return

    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY", "sk-dummy")
    base_url = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8081")
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    client_openai = OpenAI(api_key=api_key, base_url=base_url)
    
    db_path = "outputs/qdrant_db"
    client_qdrant = QdrantClient(path=db_path)
    collection_name = "knowledge_base"

    try:
        client_qdrant.get_collection(collection_name)
    except Exception as e:
        logger.error(f"Collection '{collection_name}' not found. Please run indexing script first.")
        return

    # Task 1: Embed the user query
    user_query = "What is this sample document about?"
    logger.info(f"User Query: '{user_query}'")
    logger.info(f"Embedding query using model: {model_name}")

    try:
        response = client_openai.embeddings.create(
            input=user_query,
            model=model_name
        )
        query_vector = response.data[0].embedding
        logger.info(f"Query embedded successfully. Vector dimension: {len(query_vector)}")
    except OpenAIError as e:
        logger.warning(f"API Error generating embedding for query: {e}")
        logger.warning("Falling back to local mock embedding for testing purposes.")
        import random
        random.seed(hash(user_query))
        query_vector = [random.uniform(-1, 1) for _ in range(1536)]

    # Task 2 & 3: Run top-k similarity search and include scores and metadata
    def perform_search(k):
        logger.info("-" * 80)
        logger.info(f"Performing search with k = {k}")
        logger.info("-" * 80)
        
        search_result_obj = client_qdrant.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=k,
            with_payload=True
        )
        search_result = search_result_obj.points

        logger.info(f"Retrieved {len(search_result)} results:")
        for i, hit in enumerate(search_result, start=1):
            logger.info(f"Result {i} (Score: {hit.score:.4f}):")
            logger.info(f"  Chunk ID: {hit.payload.get('chunk_id')}")
            logger.info(f"  Source: {hit.payload.get('source')}")
            logger.info(f"  Text Snippet: {hit.payload.get('text')[:100].replace(chr(10), ' ')}...")
            logger.info(f"  Metadata: {hit.payload.get('metadata')}")
            logger.info("")

    # Task 4: Demonstrate changing k
    # First with k=1
    perform_search(k=1)
    
    # Then with k=3
    perform_search(k=3)

    logger.info("=" * 80)
    logger.info("SIMILARITY SEARCH COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_similarity_search()
