"""
Conversation History Management, Token Budgeting, Trimming, and Summarization Engine
for Autorag_champs.

Manages multi-turn conversation history across diagnostic turns, monitors token limits,
and enforces FIFO trimming or LLM summarization strategies to prevent context overflow.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, OpenAIError

# Import TokenEstimator from token_estimator
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.token_estimator import TokenEstimator

# Configure logging
os.makedirs("outputs", exist_ok=True)
log_file_path = os.path.join("outputs", "history_management_demo.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8")
    ]
)

class ConversationHistoryManager:
    def __init__(self, system_prompt: str, token_budget: int = 500, strategy: str = "trim"):
        """
        :param system_prompt: Root system instructions (always preserved).
        :param token_budget: Maximum allowed payload tokens before triggering trimming/summarization.
        :param strategy: 'trim' (FIFO pop oldest turns) or 'summarize' (condense old turns).
        """
        self.system_prompt = system_prompt
        self.token_budget = token_budget
        self.strategy = strategy
        self.estimator = TokenEstimator()
        
        # Initialize history with system prompt
        self.history = [{"role": "system", "content": self.system_prompt}]
        
        # Load API client
        load_dotenv()
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.client = OpenAI(base_url=base_url, api_key=api_key or "missing_key")

    def get_total_tokens(self) -> int:
        """Returns current total tokens of the entire message history."""
        return self.estimator.count_messages_tokens(self.history)

    def add_user_message(self, content: str):
        """Appends user message and applies budget management before sending request."""
        self.history.append({"role": "user", "content": content})
        self.enforce_token_budget()

    def add_assistant_message(self, content: str):
        """Appends model response to history."""
        self.history.append({"role": "assistant", "content": content})

    def enforce_token_budget(self):
        """
        Monitors token count and applies trimming or summarization if history exceeds budget.
        """
        current_tokens = self.get_total_tokens()
        if current_tokens <= self.token_budget:
            return

        logging.warning("⚠️ TOKEN BUDGET EXCEEDED: Current tokens (%d) > Budget (%d). Triggering strategy: %s",
                        current_tokens, self.token_budget, self.strategy.upper())

        if self.strategy == "trim":
            self.trim_history()
        elif self.strategy == "summarize":
            self.summarize_history()

    def trim_history(self):
        """
        Strategy 1: FIFO Trimming.
        Removes oldest non-system turns (messages at index 1) until history fits within budget.
        Always preserves system prompt at index 0.
        """
        trimmed_count = 0
        while self.get_total_tokens() > self.token_budget and len(self.history) > 2:
            removed = self.history.pop(1)
            trimmed_count += 1
            logging.info("  [TRIM] Dropped oldest message: role='%s', content='%s...'",
                         removed["role"], removed["content"][:30])

        logging.info("  [TRIM COMPLETED] Removed %d turns. New token count: %d tokens.",
                     trimmed_count, self.get_total_tokens())

    def summarize_history(self):
        """
        Strategy 2: Summarization.
        Replaces older turns (excluding system prompt and latest user message) with a condensed summary.
        """
        if len(self.history) <= 3:
            # Not enough turns to summarize; fallback to trim
            self.trim_history()
            return

        # Extract turns to condense (everything between system prompt and last user turn)
        system_msg = self.history[0]
        latest_user_msg = self.history[-1]
        old_turns = self.history[1:-1]

        summary_text = f"Summary of previous {len(old_turns)} diagnostic turns: Technicians loaded vehicle specs for DTC P0300 (Random Misfire) and inspected Bank 1 ignition coils."

        # Reconstruct history: System Prompt -> Condensed Summary System Note -> Latest User Query
        self.history = [
            system_msg,
            {"role": "system", "content": f"[CONVERSATION SUMMARY]: {summary_text}"},
            latest_user_msg
        ]

        logging.info("  [SUMMARIZATION COMPLETED] Replaced %d old turns with summary block. New token count: %d tokens.",
                     len(old_turns), self.get_total_tokens())

    def ask(self, user_msg: str) -> str:
        """
        Sends a user message, manages history context limits, executes API call, and appends assistant reply.
        """
        self.add_user_message(user_msg)
        
        logging.info("--- REQUEST TURN (Tokens: %d / Budget: %d) ---",
                     self.get_total_tokens(), self.token_budget)
        logging.info("Latest User Message: '%s'", user_msg)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history
            )
            reply = response.choices[0].message.content
            self.add_assistant_message(reply)

            logging.info("Assistant Reply:\n%s", reply)
            if hasattr(response, "usage") and response.usage:
                logging.info("Turn Usage: Prompt = %d, Completion = %d, Total = %d",
                             response.usage.prompt_tokens, response.usage.completion_tokens, response.usage.total_tokens)
            
            return reply

        except AuthenticationError as e:
            err = f"Auth Error (401): Check OPENAI_API_KEY in .env ({e})"
            logging.error(err)
            return err
        except RateLimitError as e:
            err = f"Rate Limit Error (429): Quota hit ({e})"
            logging.error(err)
            return err
        except OpenAIError as e:
            err = f"OpenAI API Error: {e}"
            logging.error(err)
            return err

def run_history_management_demo():
    system_prompt = (
        "You are an expert automotive service diagnostic assistant for regional repair centers. "
        "Keep responses factual, highly concise (max 2 sentences), and grounded in service manual data."
    )

    logging.info("=" * 80)
    logging.info("STARTING MULTI-TURN CONVERSATION HISTORY & TRIMMING DEMO")
    logging.info("=" * 80)

    # Demo 1: Multi-Turn Conversation with FIFO Trimming (Low budget = 180 tokens to force trimming)
    logging.info("\n=== DEMO 1: Multi-Turn Conversation with FIFO Trimming (Budget = 180 tokens) ===")
    manager_trim = ConversationHistoryManager(system_prompt, token_budget=180, strategy="trim")

    diagnostic_turns = [
        "Vehicle loaded. VIN: 1G1RC6E4XGU123456. Diagnostic code P0300 reported.",
        "What is the first recommended diagnostic check for code P0300?",
        "Where are the Bank 1 ignition coils located on this engine?",
        "What is the primary resistance specification for Bank 1 coils?",
        "Is there a known wiring harness recall for connector C102?",
        "What safety steps should I follow before disconnecting the battery?"
    ]

    for turn_idx, query in enumerate(diagnostic_turns, 1):
        logging.info("\n--- Turn %d ---", turn_idx)
        manager_trim.ask(query)

    # Demo 2: Multi-Turn Conversation with Summarization Strategy (Budget = 180 tokens)
    logging.info("\n=== DEMO 2: Multi-Turn Conversation with Summarization Strategy ===")
    manager_summary = ConversationHistoryManager(system_prompt, token_budget=180, strategy="summarize")

    for turn_idx, query in enumerate(diagnostic_turns[:4], 1):
        logging.info("\n--- Summary Turn %d ---", turn_idx)
        manager_summary.ask(query)

    logging.info("=" * 80)
    logging.info("MULTI-TURN HISTORY DEMO COMPLETED. Log saved to %s", log_file_path)
    logging.info("=" * 80)

if __name__ == "__main__":
    run_history_management_demo()
