import os
import sys
import logging

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """Helper to count tokens in a string."""
    if HAS_TIKTOKEN:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
    else:
        # Simple fallback token estimator: 1 token ≈ 4 characters
        return max(1, len(text) // 4)

def assemble_augmented_prompt(
    query: str,
    retrieved_chunks: list,
    max_context_tokens: int = 2000,
    model: str = "gpt-3.5-turbo"
) -> dict:
    """
    Assembles a grounded augmented prompt.
    Task 1: Injects retrieved chunks.
    Task 2: Enforces token budget.
    Task 3: Includes source markers.
    Task 4: Adds grounding instructions.
    """
    # Task 4: Grounding Instructions
    system_instruction = (
        "You are an expert Q&A assistant. Your task is to answer the user's question "
        "using ONLY the provided CONTEXT. Do not use outside knowledge.\n"
        "If the CONTEXT does not contain enough information to answer the question, "
        "you must clearly state: 'I do not have enough information to answer that based on the provided context.'\n"
        "When answering, cite the sources used by referencing their markers (e.g., [1], [2])."
    )

    base_prompt_tokens = count_tokens(system_instruction, model) + count_tokens(query, model) + 50 # 50 for formatting overhead
    available_tokens_for_context = max_context_tokens - base_prompt_tokens

    if available_tokens_for_context <= 0:
        raise ValueError("Token budget too small even for base instructions and query.")

    context_parts = []
    current_tokens = 0

    # Task 1, 2 & 3: Inject chunks with source markers and enforce token budget
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        source_name = chunk.get("source", f"Doc-{idx}")
        chunk_text = chunk.get("text", "")
        
        # Task 3: Source Markers
        marker = f"[{idx}] Source: {source_name}"
        formatted_chunk = f"{marker}\n{chunk_text}\n\n"
        
        chunk_tokens = count_tokens(formatted_chunk, model)
        
        # Task 2: Token Budget Enforcement
        if current_tokens + chunk_tokens > available_tokens_for_context:
            logging.info(f"Token budget reached. Skipping remaining {len(retrieved_chunks) - idx + 1} chunks.")
            break
            
        context_parts.append(formatted_chunk)
        current_tokens += chunk_tokens

    assembled_context = "".join(context_parts)
    
    final_prompt = (
        f"{system_instruction}\n\n"
        f"--- CONTEXT ---\n"
        f"{assembled_context}"
        f"--- END CONTEXT ---\n\n"
        f"USER QUERY: {query}"
    )

    total_prompt_tokens = count_tokens(final_prompt, model)
    
    return {
        "final_prompt": final_prompt,
        "token_usage": total_prompt_tokens,
        "context_tokens": current_tokens,
        "budget_limit": max_context_tokens
    }

def run_context_injection_demo():
    os.makedirs("outputs", exist_ok=True)
    log_file_path = "outputs/augmented_prompt_sample.log"
    
    logger = logging.getLogger("context_injection")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    
    fh = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
    fh.setFormatter(formatter)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    
    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=" * 80)
    logger.info("CONTEXT INJECTION & PROMPT AUGMENTATION DEMO")
    logger.info("=" * 80)

    # Mock retrieved chunks
    mock_chunks = [
        {
            "source": "battery_recall_notice.pdf",
            "text": "The high voltage battery control module (BCM) in 2023 SUV models may improperly calculate thermal limits during rapid charging. This can lead to unexpected battery disconnects."
        },
        {
            "source": "service_bulletin_88B.txt",
            "text": "To resolve the false battery disconnect error, technicians must flash the BCM software to version v1.0.0 or higher. After flashing, perform a high voltage isolation test."
        },
        {
            "source": "irrelevant_marketing.pdf",
            "text": "The new 2023 SUV models feature an upgraded interior with premium leather seats and a panoramic sunroof, enhancing the driving experience."
        }
    ]
    
    # We will simulate a very tight token budget to show truncation
    # Normally this would be something like 4000 or 8000
    tight_budget = 150
    
    query = "What causes the battery disconnect error and how can it be fixed?"
    
    logger.info("Building augmented prompt with normal token budget (e.g., 2000 tokens)...")
    result_normal = assemble_augmented_prompt(query, mock_chunks, max_context_tokens=2000)
    
    logger.info(f"Total prompt tokens: {result_normal['token_usage']} / {result_normal['budget_limit']}")
    logger.info("\n=== ASSEMBLED AUGMENTED PROMPT ===")
    logger.info("\n" + result_normal["final_prompt"])
    logger.info("==================================\n")

    logger.info("Building augmented prompt with TIGHT token budget to demonstrate truncation (e.g., 150 tokens)...")
    try:
        result_tight = assemble_augmented_prompt(query, mock_chunks, max_context_tokens=150)
        logger.info(f"Total prompt tokens: {result_tight['token_usage']} / {result_tight['budget_limit']}")
        logger.info("\n=== TIGHT BUDGET AUGMENTED PROMPT ===")
        logger.info("\n" + result_tight["final_prompt"])
        logger.info("=====================================\n")
    except ValueError as e:
        logger.error(f"Failed to assemble tight budget prompt: {e}")

if __name__ == "__main__":
    run_context_injection_demo()
