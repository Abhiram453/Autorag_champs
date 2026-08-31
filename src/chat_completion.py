import os
import sys
import logging
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError, RateLimitError, APIConnectionError, OpenAIError

# Configure structured logging to both console and output log file
os.makedirs("outputs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("outputs/chat_completion.log", encoding="utf-8")
    ]
)

def create_chat_client():
    """Task 1: Configure the client from environment (.env)."""
    load_dotenv()
    
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    if not api_key:
        logging.warning("OPENAI_API_KEY is not set in environment or .env file.")

    client = OpenAI(
        base_url=base_url,
        api_key=api_key or "missing_key"
    )
    return client, model

def send_chat_completion(messages=None):
    """
    Task 2, Task 3 & Task 4: Send request, log payloads & token usage, and handle errors.
    """
    client, model = create_chat_client()

    if messages is None:
        messages = [
            {
                "role": "system",
                "content": "You are an expert automotive diagnostic assistant for service centers."
            },
            {
                "role": "user",
                "content": "What is the recommended diagnostic step when encountering fault code P0300 (random/multiple cylinder misfire)?"
            }
        ]

    # Task 3: Log outgoing request payload
    logging.info("--- REQUEST PAYLOAD ---")
    logging.info("MODEL: %s", model)
    logging.info("MESSAGES: %s", messages)

    try:
        # Task 2: Send request
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )

        reply_content = response.choices[0].message.content
        
        # Task 3: Log response payload & token usage
        logging.info("--- RESPONSE PAYLOAD ---")
        logging.info("RESPONSE CONTENT:\n%s", reply_content)

        if hasattr(response, "usage") and response.usage:
            logging.info("USAGE: Prompt Tokens = %d, Completion Tokens = %d, Total Tokens = %d",
                         response.usage.prompt_tokens,
                         response.usage.completion_tokens,
                         response.usage.total_tokens)

        # Print model response to console
        print("\n=== Model Reply ===")
        print(reply_content)
        print("===================\n")

        return response

    # Task 4: Catch and explain common errors clearly
    except AuthenticationError as e:
        logging.error("Auth failed (401): Invalid or missing API key. Check OPENAI_API_KEY in your .env file.")
        logging.error("Details: %s", e)
    except RateLimitError as e:
        logging.error("Rate limited (429): Quota hit or request rate limit exceeded. Slow down and retry with backoff.")
        logging.error("Details: %s", e)
    except APIConnectionError as e:
        logging.error("Connection failed: Could not connect to API base URL (%s). Check network connection or endpoint configuration.", os.getenv("OPENAI_BASE_URL"))
        logging.error("Details: %s", e)
    except OpenAIError as e:
        logging.error("OpenAI API Error encountered: %s", e)
    except Exception as e:
        logging.error("Unexpected error occurred during chat completion: %s", e)

if __name__ == "__main__":
    send_chat_completion()
