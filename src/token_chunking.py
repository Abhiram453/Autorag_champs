import tiktoken
from typing import List, Dict

def chunk_by_tokens(
    text: str,
    source: str,
    chunk_size: int = 500,
    overlap: int = 50,
    encoding_name: str = "cl100k_base"
) -> List[Dict]:
    """
    Split *text* into chunks of exactly *chunk_size* tokens with *overlap* tokens
    shared between consecutive chunks.

    Parameters
    ----------
    text : str
        The full plain-text content of one document.
    source : str
        Filename or path used for provenance tracking.
    chunk_size : int
        Maximum tokens per chunk.
    overlap : int
        Tokens repeated between consecutive chunks.
    encoding_name: str
        The tiktoken encoding to use. Default is "cl100k_base" (used by GPT-4).

    Returns
    -------
    list[dict]
        Each dict: {text, source, strategy, chunk_index, token_count}
    """
    if not text or not text.strip():
        return []

    encoding = tiktoken.get_encoding(encoding_name)
    tokens = encoding.encode(text)

    chunks: List[Dict] = []
    start = 0
    idx = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        
        # Decode tokens back to text
        chunk_text = encoding.decode(chunk_tokens)
        
        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "source": source,
                "strategy": "token_based",
                "chunk_index": idx,
                "token_count": len(chunk_tokens),
            })
            idx += 1

        step = max(chunk_size - overlap, 1)
        start += step

    return chunks
