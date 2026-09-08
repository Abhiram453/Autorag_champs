"""
Generation Parameters Control Engine (temperature, max_tokens, stop, top_p)
for Autorag_champs.

Demonstrates how completion parameters control model randomness, length truncation,
stop-sequence early termination, and cost optimization for automotive RAG.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Configure logging
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "parameter_comparison_results.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

class ParameterExperimentRunner:
    def __init__(self):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")

    def run_completion(self, messages, temperature=0.7, max_tokens=300, stop=None, top_p=1.0):
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "top_p": top_p
            }
            if stop:
                kwargs["stop"] = stop

            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            usage = response.usage if hasattr(response, "usage") else None
            finish_reason = response.choices[0].finish_reason if hasattr(response.choices[0], "finish_reason") else "stop"
            return content, usage, finish_reason, None
        except Exception as e:
            return None, None, None, str(e)

def run_parameter_experiments():
    runner = ParameterExperimentRunner()
    logging.info("=" * 80)
    logging.info("STARTING GENERATION PARAMETERS CONTROL EXPERIMENTS")
    logging.info("Target Model: %s", runner.model)
    logging.info("=" * 80)

    system_prompt = "You are an expert automotive service diagnostic assistant. Provide concise, factual answers."
    user_prompt = "List 3 common causes and initial diagnostic checks for DTC P0300 (random cylinder misfire)."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # --- EXPERIMENT 1: Temperature Variance Test (0.0 vs 1.0) ---
    logging.info("\n--- EXPERIMENT 1: Temperature Variance Test (0.0 vs 1.0) ---")
    
    logging.info("[1A] Temperature = 0.0 (Factual, Deterministic RAG Mode):")
    for run in range(1, 3):
        content, usage, finish, err = runner.run_completion(messages, temperature=0.0, max_tokens=150)
        if err:
            logging.error("Run %d Error: %s", run, err)
        else:
            logging.info("Run %d Content:\n%s", run, content)

    logging.info("\n[1B] Temperature = 1.0 (Creative, Variable Mode):")
    for run in range(1, 3):
        content, usage, finish, err = runner.run_completion(messages, temperature=1.0, max_tokens=150)
        if err:
            logging.error("Run %d Error: %s", run, err)
        else:
            logging.info("Run %d Content:\n%s", run, content)

    # --- EXPERIMENT 2: Max Tokens Length & Cost Cap (30 vs 250) ---
    logging.info("\n--- EXPERIMENT 2: Max Tokens Length & Cost Cap (30 vs 250) ---")
    
    logging.info("[2A] max_tokens = 30 (Truncated Output Cap):")
    content_cap, usage_cap, finish_cap, err = runner.run_completion(messages, temperature=0.1, max_tokens=30)
    if not err:
        logging.info("Content:\n%s", content_cap)
        logging.info("Finish Reason: %s (Tokens Used: %d)", finish_cap, usage_cap.completion_tokens if usage_cap else 0)

    logging.info("\n[2B] max_tokens = 250 (Full Uncapped Response):")
    content_full, usage_full, finish_full, err = runner.run_completion(messages, temperature=0.1, max_tokens=250)
    if not err:
        logging.info("Content:\n%s", content_full)
        logging.info("Finish Reason: %s (Tokens Used: %d)", finish_full, usage_full.completion_tokens if usage_full else 0)

    # --- EXPERIMENT 3: Stop Sequences Early Termination ---
    logging.info("\n--- EXPERIMENT 3: Stop Sequences Early Termination ---")
    stop_prompt = "Provide a 3-step diagnostic check for Bank 1 misfire. Separate each step with double newlines."
    stop_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": stop_prompt}
    ]

    logging.info("[3A] Without Stop Sequence:")
    content_nostop, _, _, _ = runner.run_completion(stop_messages, temperature=0.1, max_tokens=200)
    logging.info("Content:\n%s", content_nostop)

    logging.info("\n[3B] With Stop Sequence = ['\\n\\n2.', 'Step 2:'] (Stops after Step 1):")
    content_stop, _, finish_stop, _ = runner.run_completion(stop_messages, temperature=0.1, max_tokens=200, stop=["\n\n2.", "Step 2:"])
    logging.info("Content:\n%s", content_stop)
    logging.info("Finish Reason: %s", finish_stop)

    # --- EXPERIMENT 4: Recommended Grounded RAG Preset ---
    logging.info("\n--- EXPERIMENT 4: Grounded Automotive RAG Parameter Profile ---")
    logging.info("Preset: temperature=0.1, max_tokens=200, stop=['\\n\\n---\']")
    rag_content, rag_usage, rag_finish, _ = runner.run_completion(
        messages, temperature=0.1, max_tokens=200, stop=["\n\n---"]
    )
    logging.info("Grounded RAG Output:\n%s", rag_content)
    if rag_usage:
        logging.info("Total Tokens Billed: Prompt = %d, Completion = %d, Total = %d",
                     rag_usage.prompt_tokens, rag_usage.completion_tokens, rag_usage.total_tokens)

    logging.info("=" * 80)
    logging.info("PARAMETER CONTROL EXPERIMENTS COMPLETED. Saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_parameter_experiments()
