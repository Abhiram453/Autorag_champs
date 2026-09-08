import os
import sys
import logging
import json
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Add repository root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.prompt_templates import (
    VAGUE_SYSTEM_PROMPT,
    STRICT_AUTOMOTIVE_SYSTEM_PROMPT,
    JSON_CONSTRAINED_SYSTEM_PROMPT,
    PROMPT_TEST_CASES
)

# Configure logging to console and output log file
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "prompt_comparison_results.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

def init_client():
    load_dotenv()
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key or "missing_key"
    )
    return client, model

def run_single_completion(client, model, system_prompt, user_prompt):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        content = response.choices[0].message.content
        usage = response.usage if hasattr(response, "usage") else None
        return content, usage, None
    except AuthenticationError as e:
        return None, None, f"Auth Error (401): Check OPENAI_API_KEY in .env ({e})"
    except RateLimitError as e:
        return None, None, f"Rate Limit Error (429): Quota hit ({e})"
    except OpenAIError as e:
        return None, None, f"OpenAI API Error: {e}"
    except Exception as e:
        return None, None, f"Unexpected Error: {e}"

def run_prompt_experiments():
    client, model = init_client()
    logging.info("=" * 80)
    logging.info("STARTING PROMPT ENGINEERING EXPERIMENTS (System vs. User Constraints)")
    logging.info("Target Model: %s", model)
    logging.info("=" * 80)

    # Test 1: Vague vs. Specific Prompts Side-by-Side
    logging.info("\n--- EXPERIMENT 1: Vague vs. Specific Prompts Side-by-Side ---")
    test_case = PROMPT_TEST_CASES[0]
    
    # 1A: Vague System + Vague User
    content_vague, usage_vague, err_vague = run_single_completion(
        client, model, VAGUE_SYSTEM_PROMPT, test_case["vague_user_prompt"]
    )
    logging.info("[1A] System: Vague | User: '%s'", test_case["vague_user_prompt"])
    if err_vague:
        logging.error("Result: %s", err_vague)
    else:
        logging.info("Response: %s", content_vague)
        if usage_vague:
            logging.info("Usage: Tokens = %d", usage_vague.total_tokens)

    # 1B: Strict System + Specific User
    content_strict, usage_strict, err_strict = run_single_completion(
        client, model, STRICT_AUTOMOTIVE_SYSTEM_PROMPT, test_case["specific_user_prompt"]
    )
    logging.info("\n[1B] System: Strict Automotive | User: '%s'", test_case["specific_user_prompt"])
    if err_strict:
        logging.error("Result: %s", err_strict)
    else:
        logging.info("Response: %s", content_strict)
        if usage_strict:
            logging.info("Usage: Tokens = %d", usage_strict.total_tokens)

    # Test 2: Out-of-Scope Question & Refusal Rule
    logging.info("\n--- EXPERIMENT 2: Scope & Refusal Rules ('I don't know') ---")
    out_of_scope_query = PROMPT_TEST_CASES[1]["vague_user_prompt"]
    
    content_refusal, usage_refusal, err_refusal = run_single_completion(
        client, model, STRICT_AUTOMOTIVE_SYSTEM_PROMPT, out_of_scope_query
    )
    logging.info("[2] Out-of-Scope Query: '%s'", out_of_scope_query)
    if err_refusal:
        logging.error("Result: %s", err_refusal)
    else:
        logging.info("Response: %s", content_refusal)

    # Test 3: Format Constraint (JSON Output Schema)
    logging.info("\n--- EXPERIMENT 3: Format Constraints (Strict JSON Schema) ---")
    json_query = "Parse ignition coil specs for P0300 on Bank 1. Primary resistance is 0.5 ohms."
    
    content_json, usage_json, err_json = run_single_completion(
        client, model, JSON_CONSTRAINED_SYSTEM_PROMPT, json_query
    )
    logging.info("[3] JSON Constrained Query: '%s'", json_query)
    if err_json:
        logging.error("Result: %s", err_json)
    else:
        logging.info("Raw Model Output:\n%s", content_json)
        try:
            parsed = json.loads(content_json)
            logging.info("JSON Parsing Verification: SUCCESS! Parsed keys: %s", list(parsed.keys()))
        except Exception:
            logging.warning("JSON Parsing Verification: FAILED (Model output was not strict JSON)")

    logging.info("=" * 80)
    logging.info("PROMPT EXPERIMENTS COMPLETED. Results written to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_prompt_experiments()
