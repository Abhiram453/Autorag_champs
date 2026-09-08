import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

# Try importing OpenAI client
try:
    from openai import OpenAI, OpenAIError
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

def run_api_embedding():
    # Setup logging
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/api_embedding_output.log"
    
    logger = logging.getLogger("api_embedding")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("GENERATING EMBEDDINGS VIA API")
    logger.info("=" * 80)

    # Task 3: Use environment config
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_name = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    if not api_key or api_key == "sk-your-real-key-here":
        logger.error("No valid OPENAI_API_KEY found in environment. Please set it in .env")
        return

    if not HAS_OPENAI:
        logger.error("The 'openai' library is not installed. Please run pip install openai")
        return

    # Task 1 & 2: Generate embeddings and store vectors with source chunks
    from src.document_loader import load_corpus
    from src.text_cleaning import clean_text
    from src.chunk_metadata import chunk_corpus_with_metadata

    data_dir = Path("data")
    if not data_dir.exists():
        logger.error(f"Data directory {data_dir} not found.")
        return

    docs, _ = load_corpus(data_dir)
    for doc in docs:
        doc["text"] = clean_text(doc["text"])
        
    corpus_chunks = chunk_corpus_with_metadata(docs)
    
    # Take a small subset (e.g. 3 chunks) for the sample corpus
    sample_corpus = corpus_chunks[:3]
    logger.info(f"Loaded sample corpus with {len(sample_corpus)} chunks.")
    
    # Initialize the client
    client = OpenAI(api_key=api_key, base_url=base_url)
    logger.info(f"Connected to API at {base_url} using model '{model_name}'")

    embedded_corpus = []

    for i, chunk in enumerate(sample_corpus):
        logger.info(f"Generating embedding for chunk {i+1}/{len(sample_corpus)} (ID: {chunk.get('chunk_id')})")
        text_to_embed = chunk["text"]
        
        try:
            response = client.embeddings.create(
                input=text_to_embed,
                model=model_name
            )
            vector = response.data[0].embedding
            
            # Create a combined record
            record = {
                "chunk_id": chunk.get("chunk_id"),
                "source": chunk.get("source"),
                "section_title": chunk.get("section_title"),
                "text": text_to_embed,
                "metadata": chunk, # store all metadata
                "embedding": vector
            }
            embedded_corpus.append(record)
        except OpenAIError as e:
            logger.error(f"API Error generating embedding: {e}")
            return
            
    # Task 4: Print verification output
    logger.info("\n" + "=" * 80)
    logger.info("VERIFICATION OUTPUT")
    logger.info("=" * 80)
    logger.info(f"Total chunks embedded:  {len(embedded_corpus)}")
    
    if embedded_corpus:
        sample_vector = embedded_corpus[0]["embedding"]
        logger.info(f"Vector dimensions:      {len(sample_vector)}")
        
        trimmed_vector = [round(v, 6) for v in sample_vector[:5]]
        logger.info(f"Sample vector values:   {trimmed_vector} ...")
        
        # Verify consistent dimensions
        all_same_dim = all(len(c["embedding"]) == len(sample_vector) for c in embedded_corpus)
        logger.info(f"Dimensions match across all vectors: {all_same_dim}")
    
    # Save the embedded corpus
    out_file = Path("outputs/embedded_corpus.json")
    with open(out_file, "w", encoding="utf-8") as f:
        # Save a truncated version of the vectors for the sample file to keep it readable, 
        # or full if needed. We will save full vectors.
        json.dump(embedded_corpus, f, indent=2)
        
    logger.info(f"Saved embedded corpus to {out_file}")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_api_embedding()
