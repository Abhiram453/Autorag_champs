"""
Prompt Template Engine & Multi-Feature Reuse Engine for Autorag_champs.

Demonstrates decoupled prompt management: imports templates from prompts/templates.py,
injects dynamic runtime variables ({context}, {question}, {vehicle_model}, {dtc_code}),
and reuses a single template across multiple application features.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Import templates and renderer from prompts.templates
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.templates import (
    RAG_ANSWER_TEMPLATE,
    JSON_DIAGNOSTIC_TEMPLATE,
    SYSTEM_PERSONA_TEMPLATE,
    render_prompt
)

# Configure logging
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "prompt_templates_demo.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

class PromptTemplateEngine:
    def __init__(self):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")

    def execute_completion(self, system_prompt: str, user_prompt: str):
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1
            )
            return response.choices[0].message.content, response.usage, None
        except Exception as e:
            return None, None, str(e)

    def feature_chat_endpoint(self, vehicle_model: str, dtc_code: str, context: str, question: str):
        """Feature 1: Web Chat Endpoint consuming RAG_ANSWER_TEMPLATE."""
        system = render_prompt(SYSTEM_PERSONA_TEMPLATE, region_code="GLOBAL", role_focus="Interactive Web Assistant")
        user_msg = render_prompt(
            RAG_ANSWER_TEMPLATE,
            vehicle_model=vehicle_model,
            dtc_code=dtc_code,
            context=context,
            question=question
        )
        content, usage, err = self.execute_completion(system, user_msg)
        return content, user_msg, err

    def feature_batch_evaluator(self, vehicle_model: str, dtc_code: str, context: str, question: str):
        """Feature 2: Batch RAG Quality Evaluator consuming the EXACT SAME RAG_ANSWER_TEMPLATE."""
        system = render_prompt(SYSTEM_PERSONA_TEMPLATE, region_code="GLOBAL", role_focus="Batch Benchmark Evaluator")
        user_msg = render_prompt(
            RAG_ANSWER_TEMPLATE,
            vehicle_model=vehicle_model,
            dtc_code=dtc_code,
            context=context,
            question=question
        )
        content, usage, err = self.execute_completion(system, user_msg)
        return content, user_msg, err

    def feature_cli_service_tool(self, vehicle_model: str, dtc_code: str, context: str, question: str):
        """Feature 3: Terminal CLI Tool consuming the EXACT SAME RAG_ANSWER_TEMPLATE."""
        system = render_prompt(SYSTEM_PERSONA_TEMPLATE, region_code="GLOBAL", role_focus="Terminal CLI Service Diagnostics")
        user_msg = render_prompt(
            RAG_ANSWER_TEMPLATE,
            vehicle_model=vehicle_model,
            dtc_code=dtc_code,
            context=context,
            question=question
        )
        content, usage, err = self.execute_completion(system, user_msg)
        return content, user_msg, err

def run_prompt_template_demo():
    engine = PromptTemplateEngine()
    logging.info("=" * 80)
    logging.info("STARTING PROMPT TEMPLATE & MULTI-FEATURE REUSE DEMO")
    logging.info("Target Model: %s", engine.model)
    logging.info("=" * 80)

    # Sample Dynamic Runtime Variables
    sample_context = (
        "Manual Chunk MNL-24-001: For DTC P0300 on 2023 SUV Model X, inspect Bank 1 ignition coils. "
        "Primary resistance must measure 0.4 to 0.6 ohms across terminals 1 and 2. Connector C102 must be checked for corrosion."
    )
    sample_question = "What is the primary resistance spec and connector check for Bank 1 coils?"
    vehicle_model = "2023 SUV Model X"
    dtc_code = "P0300"

    # --- 1. Template Rendering & Variable Injection ---
    logging.info("\n--- 1. Template Rendering Test (Variable Injection) ---")
    rendered_user_msg = render_prompt(
        RAG_ANSWER_TEMPLATE,
        vehicle_model=vehicle_model,
        dtc_code=dtc_code,
        context=sample_context,
        question=sample_question
    )
    logging.info("Rendered User Message:\n%s", rendered_user_msg)

    # --- 2. Multi-Feature Reuse of Single Prompt Template ---
    logging.info("\n--- 2. Multi-Feature Reuse (1 Template -> 3 Features) ---")
    
    # Feature 1 Output
    reply1, msg1, err1 = engine.feature_chat_endpoint(vehicle_model, dtc_code, sample_context, sample_question)
    logging.info("[Feature 1: Interactive Chat Endpoint]")
    logging.info("  Reply: %s", reply1)

    # Feature 2 Output
    reply2, msg2, err2 = engine.feature_batch_evaluator(vehicle_model, dtc_code, sample_context, sample_question)
    logging.info("[Feature 2: Batch Quality Evaluator]")
    logging.info("  Reply: %s", reply2)

    # Feature 3 Output
    reply3, msg3, err3 = engine.feature_cli_service_tool(vehicle_model, dtc_code, sample_context, sample_question)
    logging.info("[Feature 3: Terminal CLI Service Tool]")
    logging.info("  Reply: %s", reply3)

    # --- 3. Zero Prompt Drift Verification ---
    logging.info("\n--- 3. Prompt Consistency Verification ---")
    if msg1 == msg2 == msg3:
        logging.info("✅ SUCCESS: All 3 features generated 100% IDENTICAL prompt strings from prompts/templates.py!")
    else:
        logging.warning("⚠️ Prompt drift detected across features.")

    logging.info("=" * 80)
    logging.info("PROMPT TEMPLATE DEMO COMPLETED. Saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_prompt_template_demo()
