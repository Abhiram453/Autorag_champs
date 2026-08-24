# Automotive RAG Assistant (`Autorag_champs`)

An AI-powered automotive diagnostic assistant that retrieves model-specific, up-to-date repair manuals, recall notices, and diagnostic guides for service centers across regions.

---

## 📁 Repository Structure

```
Autorag_champs/
├── data/              # Source repair manuals, recall notices, diagnostic guides (git-ignored)
├── src/               # Ingestion, embedding, retrieval, and chat completion code
│   └── chat_completion.py  # OpenAI-compatible API client & chat completion handler
├── prompts/           # System prompt templates & persona instructions
│   └── system_prompt.txt
├── outputs/           # Logs, generated output artifacts, sample execution captures
│   └── sample_output.txt
├── .env               # Local environment variables and API keys (git-ignored)
├── .env.example       # Example environment configuration template (committed)
├── .gitignore         # Version control exclusion rules
├── requirements.txt   # Python project dependencies
└── README.md          # Project documentation
```

---

## ⚙️ Setup & Configuration

### 1. Environment Isolation
Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env` and fill in your API configuration:
```bash
cp .env.example .env
```
Edit `.env`:
```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_actual_api_key_here
CHAT_MODEL=gpt-4o-mini
```
*(Supports any OpenAI-compatible provider, including local runtimes like Ollama or LM Studio).*

---

## 🚀 Running the Chat Completion Client

To execute a chat completion request with structured logging and error handling:

```bash
python src/chat_completion.py
```

### Key Features
- **Environment Configured (Task 1)**: Base URL, API key, and model read strictly from `.env`.
- **Request & Response Handling (Task 2)**: Sends chat completion requests using system & user role messages, outputting `choices[0].message.content`.
- **Structured Logging (Task 3)**: Logs request payload, model response text, and token usage (`prompt_tokens`, `completion_tokens`, `total_tokens`) to stdout and `outputs/chat_completion.log`.
- **Clear Error Handling (Task 4)**: Catches and formats `401 Unauthorized` (`AuthenticationError`), `429 Too Many Requests` (`RateLimitError`), and `APIConnectionError` with clear human-readable messages instead of raw stack traces.
- **Sample Output (Task 5)**: Saved sample logs and execution outputs in `outputs/sample_output.txt`.