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

def lexical_overlap_score(query, text):
    """Fallback custom scoring method for re-ranking"""
    query_words = set("".join(c for c in query.lower() if c.isalnum() or c.isspace()).split())
    text_words = set("".join(c for c in text.lower() if c.isalnum() or c.isspace()).split())
    intersection = query_words.intersection(text_words)
    return len(intersection) / len(query_words) if query_words else 0

def run_chunk_reranking():
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/chunk_reranking_results.log"
    
    logger = logging.getLogger("chunk_reranking")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("CHUNK RE-RANKING FOR PRECISION")
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

    user_query = "What is this sample document about?"
    logger.info(f"User Query: '{user_query}'")

    try:
        response = client_openai.embeddings.create(
            input=user_query,
            model=model_name
        )
        query_vector = response.data[0].embedding
    except OpenAIError as e:
        logger.warning(f"API Error generating embedding: {e}")
        logger.warning("Falling back to local mock embedding.")
        import random
        random.seed(hash(user_query))
        query_vector = [random.uniform(-1, 1) for _ in range(1536)]

    # Task 1: Retrieve a larger candidate set (k=10)
    initial_k = 10
    final_k = 3
    
    logger.info("-" * 80)
    logger.info(f"Retrieving initial candidate set of size {initial_k}")
    logger.info("-" * 80)
    
    search_result_obj = client_qdrant.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=initial_k,
        with_payload=True
    )
    candidates = search_result_obj.points

    logger.info("Initial Ranking (Original Vector Scores):")
    for i, hit in enumerate(candidates, start=1):
        snippet = hit.payload.get('text', '')[:60].replace(chr(10), ' ')
        logger.info(f"  Rank {i} | Score: {hit.score:.4f} | Chunk ID: {hit.payload.get('chunk_id')} | Snippet: {snippet}...")

    # Task 2: Re-rank candidates
    logger.info("-" * 80)
    logger.info("Re-ranking candidates using custom lexical overlap scoring")
    logger.info("-" * 80)
    
    reranked_candidates = []
    for hit in candidates:
        text = hit.payload.get("text", "")
        rerank_score = lexical_overlap_score(user_query, text)
        
        reranked_candidates.append({
            "chunk_id": hit.payload.get("chunk_id"),
            "original_score": hit.score,
            "rerank_score": rerank_score,
            "text": text,
            "metadata": hit.payload.get("metadata", {}),
            "source": hit.payload.get("source")
        })

    # Sort by re-rank score descending
    reranked_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)

    # Task 3 & 4: Show improved top results and compare before/after
    logger.info("Before-and-After Ordering Comparison:")
    logger.info("Original Top 3:")
    for i in range(min(final_k, len(candidates))):
        hit = candidates[i]
        snippet = hit.payload.get('text', '')[:100].replace(chr(10), ' ')
        logger.info(f"  [{i+1}] Score: {hit.score:.4f} | Text: {snippet}...")
        
    logger.info("\nRe-ranked Top 3:")
    for i in range(min(final_k, len(reranked_candidates))):
        candidate = reranked_candidates[i]
        snippet = candidate['text'][:100].replace(chr(10), ' ')
        logger.info(f"  [{i+1}] Re-rank Score: {candidate['rerank_score']:.4f} (Original: {candidate['original_score']:.4f})")
        logger.info(f"      Chunk ID: {candidate['chunk_id']}")
        logger.info(f"      Metadata: {candidate['metadata']}")
        logger.info(f"      Text: {snippet}...")

    logger.info("=" * 80)
    logger.info("CHUNK RE-RANKING COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_chunk_reranking()
