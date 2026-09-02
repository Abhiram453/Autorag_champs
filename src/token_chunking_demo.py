import sys
import os

# Ensure the src directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from token_chunking import chunk_by_tokens

def demonstrate_boundary_context():
    print("--- Task 3: Show overlap preserving boundary context ---")
    # A text specifically designed so that an important idea crosses the chunk boundary.
    # We will use a very small chunk size to demonstrate this easily.
    text = (
        "The transmission fluid must be replaced every 30,000 miles to ensure optimal performance. "
        "Failure to do so can result in catastrophic gearbox failure and void the warranty."
    )
    
    print(f"Original Text: {text}\n")
    
    # Let's chunk without overlap. We will choose a chunk size that splits the text right in the middle of the second sentence.
    # "catastrophic gearbox failure" will be split.
    # The text has about 32 tokens. Let's use chunk_size=24.
    
    chunks_no_overlap = chunk_by_tokens(text, source="demo", chunk_size=24, overlap=0)
    print(">>> Without Overlap (chunk_size=24, overlap=0):")
    for chunk in chunks_no_overlap:
        print(f"Chunk {chunk['chunk_index']} ({chunk['token_count']} tokens): '{chunk['text']}'")
        
    print("\nNotice how the idea of 'catastrophic gearbox failure' might be split between chunks.")
    
    # Now with overlap
    chunks_with_overlap = chunk_by_tokens(text, source="demo", chunk_size=24, overlap=10)
    print("\n>>> With Overlap (chunk_size=24, overlap=10):")
    for chunk in chunks_with_overlap:
        print(f"Chunk {chunk['chunk_index']} ({chunk['token_count']} tokens): '{chunk['text']}'")
        
    print("\nNotice how Chunk 1 now retains enough of the previous chunk to provide full context.")
    print("-" * 60 + "\n")


def justify_settings():
    print("--- Task 4: Justify size + overlap ---")
    justification = (
        "Justification for Token Size & Overlap for Gemini/OpenAI Embedding Models:\n\n"
        "- Chunk Size (e.g., 500 tokens): Most embedding models (like text-embedding-3-small) "
        "have context windows (e.g., 8192 tokens), but retrieval accuracy often degrades if chunks are too large, "
        "as the embedding becomes 'diluted' with multiple topics. 500 tokens roughly translates to ~350-400 words, "
        "which is a sweet spot for capturing a complete thought or a short section in an automotive manual.\n"
        "- Overlap (e.g., 50 tokens): 50 tokens is roughly 1-2 sentences. This controlled overlap ensures that any "
        "idea sitting exactly on the boundary is not lost. It prevents the system from 'missing' a query that targets "
        "the boundary. We don't make it larger (e.g., 200 tokens) because that would significantly increase the total "
        "token count of our chunked dataset, thereby increasing the vector database storage cost and API embedding cost, "
        "while providing diminishing returns on context preservation."
    )
    print(justification)
    print("-" * 60 + "\n")


def sample_output():
    print("--- Task 5: Sample Output on a Document ---")
    # Read a sample document
    doc_path = os.path.join(os.path.dirname(__file__), "..", "data", "tsb_notice.md")
    if not os.path.exists(doc_path):
        print(f"Error: Could not find document at {doc_path}")
        return
        
    with open(doc_path, "r", encoding="utf-8") as f:
        text = f.read()
        
    # We will use our justified settings
    chunk_size = 500
    overlap = 50
    
    chunks = chunk_by_tokens(text, source="tsb_notice.md", chunk_size=chunk_size, overlap=overlap)
    
    print(f"Total Chunks Generated: {len(chunks)}\n")
    
    for i, chunk in enumerate(chunks):
        # Print a preview of the chunk
        preview = chunk['text'].replace('\n', ' ')
        if len(preview) > 100:
            preview = preview[:100] + "..."
        print(f"Chunk {chunk['chunk_index']} | Tokens: {chunk['token_count']} | Preview: {preview}")

if __name__ == "__main__":
    demonstrate_boundary_context()
    justify_settings()
    sample_output()
