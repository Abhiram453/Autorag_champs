"""
Structured Output & Safe JSON Parsing / Validation Engine for Autorag_champs.

Prompts OpenAI-compatible models for defined JSON schemas, defensively parses outputs,
validates required fields and types, and implements retry recovery for malformed responses.
"""

import os
import sys
import logging
import json
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Configure logging
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "structured_output_demo.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

class StructuredOutputParser:
    def __init__(self):
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")

    def request_completion(self, messages, json_mode=True):
        """Sends chat completion request with optional JSON mode response format."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.0  # Factual, deterministic
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content, response.usage, None
        except Exception as e:
            return None, None, str(e)

    def safe_parse_json(self, raw_text: str):
        """
        Defensive JSON Parser:
        Parses raw model output string with json.loads, catching JSONDecodeError safely.
        """
        if not raw_text:
            return None, "Empty response received"
        
        # Clean potential markdown wrapping if returned as ```json ... ```
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        try:
            parsed_data = json.loads(cleaned_text)
            return parsed_data, None
        except json.JSONDecodeError as e:
            return None, f"JSONDecodeError: Malformed JSON syntax ({e})"

    def validate_schema(self, data: dict, required_keys: list, type_checks: dict = None):
        """
        Schema & Field Validator:
        Verifies all required keys are present and validates data types.
        """
        if not isinstance(data, dict):
            return False, "Parsed JSON root is not a dict"

        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            return False, f"Missing required keys: {missing_keys}"

        if type_checks:
            for key, expected_type in type_checks.items():
                if key in data and not isinstance(data[key], expected_type):
                    return False, f"Type mismatch for key '{key}': Expected {expected_type.__name__}, got {type(data[key]).__name__}"

        return True, "Schema validation PASSED"

    def query_with_json_retry(self, user_query: str, system_schema_prompt: str, required_keys: list, max_retries: int = 1):
        """
        Executes query, parses JSON, validates schema, and retries once with reminder prompt if needed.
        """
        messages = [
            {"role": "system", "content": system_schema_prompt},
            {"role": "user", "content": user_query}
        ]

        attempt = 0
        while attempt <= max_retries:
            attempt += 1
            logging.info("--- Execution Attempt %d / %d ---", attempt, max_retries + 1)
            
            raw_output, usage, err = self.request_completion(messages, json_mode=True)
            if err:
                logging.error("API Call Error: %s", err)
                return None, f"API Error: {err}"

            logging.info("Raw Model Output:\n%s", raw_output)

            # Step 1: Safe Parsing
            parsed_data, parse_err = self.safe_parse_json(raw_output)
            if parse_err:
                logging.warning("⚠️ Parse Error on Attempt %d: %s", attempt, parse_err)
                if attempt <= max_retries:
                    messages.append({"role": "assistant", "content": raw_output})
                    messages.append({
                        "role": "user",
                        "content": f"Your previous response had a syntax error ({parse_err}). Return ONLY valid JSON."
                    })
                    continue
                return None, parse_err

            # Step 2: Schema Validation
            is_valid, validation_msg = self.validate_schema(parsed_data, required_keys)
            if not is_valid:
                logging.warning("⚠️ Validation Failure on Attempt %d: %s", attempt, validation_msg)
                if attempt <= max_retries:
                    messages.append({"role": "assistant", "content": raw_output})
                    messages.append({
                        "role": "user",
                        "content": f"Your previous response was missing required keys ({validation_msg}). Include all keys: {required_keys}."
                    })
                    continue
                return None, validation_msg

            logging.info("✅ SUCCESS: %s", validation_msg)
            return parsed_data, None

        return None, "Max retries exceeded"

def run_structured_output_demo():
    parser = StructuredOutputParser()
    logging.info("=" * 80)
    logging.info("STARTING STRUCTURED OUTPUT & SAFE JSON VALIDATION DEMO")
    logging.info("Target Model: %s", parser.model)
    logging.info("=" * 80)

    # Example 1: Standard Diagnostic Schema Extraction
    logging.info("\n--- DEMO 1: Diagnostic Specs Extraction (Valid JSON Mode) ---")
    system_prompt = (
        "You are an automated automotive diagnostic parser.\n"
        "You MUST respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "fault_code": "string",\n'
        '  "recommended_action": "string",\n'
        '  "source_manual": "string",\n'
        '  "connector_id": "string or null",\n'
        '  "confidence": "number between 0.0 and 1.0"\n'
        "}\n"
        "Do not include any prose, markdown wrapping, or explanations outside the JSON."
    )
    user_query = "Parse DTC P0300 misfire troubleshooting steps for Bank 1 ignition coils according to manual MNL-24-001. Check connector C102."
    required_keys = ["fault_code", "recommended_action", "source_manual", "confidence"]

    result, err = parser.query_with_json_retry(user_query, system_prompt, required_keys)
    if err:
        logging.error("Demo 1 Failed: %s", err)
    else:
        logging.info("Parsed Result Object:")
        logging.info("  Fault Code: %s", result.get("fault_code"))
        logging.info("  Action: %s", result.get("recommended_action"))
        logging.info("  Source Manual: %s", result.get("source_manual"))
        logging.info("  Connector ID: %s", result.get("connector_id"))
        logging.info("  Confidence: %s", result.get("confidence"))

    # Example 2: Simulating Defensive JSON Parsing & Field Validation Failure Recovery
    logging.info("\n--- DEMO 2: Defensive JSON Parser & Field Validation Verification ---")
    raw_sample_valid = '{"answer": "Inspect coil resistance", "source": "MNL-24-001", "confidence": 0.95}'
    raw_sample_malformed = '{"answer": "Inspect coil resistance", "source": "MNL-24-001", }'  # trailing comma
    raw_sample_missing_key = '{"answer": "Inspect coil resistance"}'

    logging.info("Testing Valid Raw String:")
    data1, err1 = parser.safe_parse_json(raw_sample_valid)
    valid1, msg1 = parser.validate_schema(data1, ["answer", "source", "confidence"]) if data1 else (False, err1)
    logging.info("  Parsed: %s | Schema Check: %s", data1, msg1)

    logging.info("Testing Malformed JSON String (Trailing Comma):")
    data2, err2 = parser.safe_parse_json(raw_sample_malformed)
    logging.info("  Parsed Data: %s | Handled Error: %s", data2, err2)

    logging.info("Testing Missing Required Key ('source', 'confidence'):")
    data3, err3 = parser.safe_parse_json(raw_sample_missing_key)
    valid3, msg3 = parser.validate_schema(data3, ["answer", "source", "confidence"])
    logging.info("  Parsed Data: %s | Validation Result: %s", data3, msg3)

    logging.info("=" * 80)
    logging.info("STRUCTURED OUTPUT DEMO COMPLETED. Log saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_structured_output_demo()
