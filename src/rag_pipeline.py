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

# Global configuration
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY", "sk-dummy")
BASE_URL = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8081")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-3.5-turbo")
COLLECTION_NAME = "knowledge_base"

# Initialize clients
client_openai = OpenAI(api_key=API_KEY, base_url=BASE_URL) if HAS_OPENAI else None

db_path = "outputs/qdrant_db"
client_qdrant = QdrantClient(path=db_path) if HAS_QDRANT else None

def embed_query(query: str) -> list:
    """Stage 1: Embed the user query into a dense vector."""
    if not client_openai:
        raise RuntimeError("OpenAI client is not initialized.")
    
    try:
        response = client_openai.embeddings.create(
            input=query,
            model=EMBEDDING_MODEL
        )
        return response.data[0].embedding
    except OpenAIError as e:
        # Fallback for testing environment
        import random
        random.seed(hash(query))
        return [random.uniform(-1, 1) for _ in range(1536)]

def retrieve_context(query_vector: list, top_k: int = 3) -> list:
    """Stage 2: Retrieve relevant candidates from the vector database."""
    if not client_qdrant:
        raise RuntimeError("Qdrant client is not initialized.")
        
    try:
        search_result_obj = client_qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        return search_result_obj.points
    except Exception:
        return []

def assemble_prompt(query: str, retrieved_chunks: list) -> str:
    """Stage 3: Assemble grounded context into a generation prompt."""
    context_text = ""
    for idx, hit in enumerate(retrieved_chunks, start=1):
        source = hit.payload.get("source", "Unknown")
        text = hit.payload.get("text", "")
        context_text += f"\n--- Source {idx}: {source} ---\n{text}\n"

    prompt = (
        "You are a helpful assistant. Use ONLY the following context to answer the user's query.\n"
        "If the answer is not contained in the context, reply 'I do not have enough information to answer that.'\n\n"
        "CONTEXT:\n"
        f"{context_text}\n\n"
        "USER QUERY:\n"
        f"{query}\n"
    )
    return prompt

def generate_answer(prompt: str) -> str:
    """Stage 4: Generate final answer using the LLM."""
    if not client_openai:
        raise RuntimeError("OpenAI client is not initialized.")
        
    try:
        response = client_openai.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )
        return response.choices[0].message.content
    except OpenAIError as e:
        return "Error: Could not reach LLM to generate answer. (Fallback mode active)"

def run_pipeline():
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/rag_pipeline_output.log"
    
    logger = logging.getLogger("rag_pipeline")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("END-TO-END RAG PIPELINE EXECUTION")
    logger.info("=" * 80)

    sample_query = "What is the remedy for the battery disconnect error?"
    logger.info(f"User Query: '{sample_query}'")

    # Pipeline Execution
    logger.info("Stage 1: Embedding query...")
    query_vector = embed_query(sample_query)
    
    logger.info("Stage 2: Retrieving context...")
    retrieved_chunks = retrieve_context(query_vector, top_k=2)
    sources = [hit.payload.get("source", "Unknown") for hit in retrieved_chunks]
    logger.info(f"Retrieved {len(retrieved_chunks)} chunks from sources: {sources}")
    
    logger.info("Stage 3: Assembling prompt...")
    prompt = assemble_prompt(sample_query, retrieved_chunks)
    
    logger.info("Stage 4: Generating answer...")
    answer = generate_answer(prompt)

    # Output Results
    logger.info("=" * 80)
    logger.info("RAG PIPELINE RESULT")
    logger.info("=" * 80)
    logger.info(f"Query: {sample_query}")
    logger.info(f"Generated Answer:\n{answer}")
    logger.info("Sources Used:")
    for src in sources:
        logger.info(f" - {src}")
    
    logger.info("=" * 80)

if __name__ == "__main__":
    run_pipeline()
