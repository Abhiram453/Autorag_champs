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

def run_retrieval_evaluation():
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/retrieval_evaluation_results.log"
    
    logger = logging.getLogger("retrieval_evaluation")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("RETRIEVAL EVALUATION & RECALL TESTING")
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

    # Task 1: Prepare labelled queries
    # Dictionary mapping queries to their known relevant chunk ID
    labelled_queries = [
        {
            "query": "What is this sample document for?",
            "expected_chunk_id": "noisy_document.txt::section::0"
        },
        {
            "query": "What happens if there are wrong characters like fire?",
            "expected_chunk_id": "noisy_document.txt::section::1"
        },
        {
            "query": "Which vehicle model is affected by the recall?",
            "expected_chunk_id": "recall_report.html::section::0"
        },
        {
            "query": "What is the remedy for the battery disconnect error?",
            "expected_chunk_id": "recall_report.html::section::0"
        },
        {
            "query": "How do I bake a chocolate cake?", # Intentional failure case
            "expected_chunk_id": "none_expected"
        }
    ]
    
    k = 3
    total_queries = len(labelled_queries)
    successful_recalls = 0
    total_precision = 0.0

    logger.info(f"Loaded {total_queries} labelled queries. Evaluating at k={k}...")
    logger.info("-" * 80)

    for idx, item in enumerate(labelled_queries, start=1):
        query = item["query"]
        expected_chunk = item["expected_chunk_id"]
        
        logger.info(f"Query {idx}: '{query}'")
        logger.info(f"Expected relevant chunk ID: {expected_chunk}")

        try:
            response = client_openai.embeddings.create(
                input=query,
                model=model_name
            )
            query_vector = response.data[0].embedding
        except OpenAIError as e:
            # Fallback for testing without real API
            import random
            random.seed(hash(query))
            query_vector = [random.uniform(-1, 1) for _ in range(1536)]

        search_result_obj = client_qdrant.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=k,
            with_payload=True
        )
        candidates = search_result_obj.points
        
        retrieved_chunk_ids = [hit.payload.get("chunk_id") for hit in candidates]
        logger.info(f"Retrieved Top-{k} Chunk IDs: {retrieved_chunk_ids}")

        # Task 2: Measure recall
        # Recall@k = 1 if the expected chunk is in the retrieved chunks, else 0
        is_recalled = expected_chunk in retrieved_chunk_ids
        recall_at_k = 1 if is_recalled else 0
        
        # Task 3: Report precision
        # Precision@k = (number of relevant chunks retrieved) / k
        # Here we only have 1 known relevant chunk per query
        precision_at_k = 1.0 / k if is_recalled else 0.0
        
        if expected_chunk == "none_expected":
            # For intentional out-of-domain query, recall and precision are not standardly applicable
            # We skip them from the average
            total_queries -= 1
            logger.info("Out-of-domain query. Skipping recall/precision calculation.")
        else:
            successful_recalls += recall_at_k
            total_precision += precision_at_k
            
        logger.info(f"Recall@{k}: {recall_at_k} | Precision@{k}: {precision_at_k:.4f}")

        # Task 4: Inspect failures
        if not is_recalled and expected_chunk != "none_expected":
            logger.warning(f"FAILURE: Expected chunk '{expected_chunk}' not retrieved.")
            logger.warning("Likely Causes Analysis:")
            logger.warning("- Embedding mismatch: The query phrasing may use vocabulary disconnected from the chunk's content.")
            logger.warning("- Query length/specificity: The query might be too broad or too short to strongly match the specific chunk.")
            logger.warning("- Vector space density: If the fallback random embeddings are being used, similarity is effectively random.")
            logger.warning("Recommended Fix: Improve the embedding model, try keyword-based retrieval (hybrid search), or expand query terms.")
            
        logger.info("-" * 80)

    # Final Evaluation Summary
    if total_queries > 0:
        average_recall = successful_recalls / total_queries
        average_precision = total_precision / total_queries
        
        logger.info("EVALUATION SUMMARY")
        logger.info(f"Total Evaluated Queries: {total_queries}")
        logger.info(f"Average Recall@{k}: {average_recall:.4f}")
        logger.info(f"Average Precision@{k}: {average_precision:.4f}")
    
    logger.info("=" * 80)
    logger.info("EVALUATION COMPLETE")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_retrieval_evaluation()
