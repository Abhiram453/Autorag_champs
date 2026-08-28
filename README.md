# Automotive RAG Assistant (`Autorag_champs`)

An AI-powered automotive diagnostic assistant that retrieves model-specific, up-to-date repair manuals, recall notices, and diagnostic guides for service centers across regions.

---

## 📁 Repository Structure

```
Autorag_champs/
├── .github/           # Issue and Pull Request templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/sprint_task.md
├── data/              # Source repair manuals, recall notices, diagnostic guides (git-ignored)
├── src/               # Ingestion, embedding, retrieval, parameters, and history code
│   ├── chat_completion.py    # OpenAI-compatible API client & chat completion handler
│   ├── prompt_experiment.py  # Side-by-side prompt engineering experiment runner
│   ├── token_estimator.py    # Token counter, cost calculator & corpus scale estimator
│   ├── history_manager.py    # Multi-turn conversation manager, FIFO trimming & summarization
│   ├── parameter_experiment.py # Generation parameters control (temperature, max_tokens, stop)
│   └── structured_output.py  # Defensive JSON mode parser, schema validator & retry recovery
├── prompts/           # System prompt templates & persona instructions
│   ├── system_prompt.txt
│   └── prompt_templates.py   # Vague vs. Strict System Prompts, Refusal Rules & JSON schemas
├── outputs/           # Logs, generated output artifacts, sample execution captures
│   ├── sample_output.txt
│   ├── prompt_comparison_results.log # Execution trace of side-by-side prompt tests
│   ├── token_cost_analysis.log      # Token counting, call costs & corpus scale budget
│   ├── history_management_demo.log  # Multi-turn history, trimming & summarization logs
│   ├── parameter_comparison_results.log # Generation parameters control test logs
│   ├── structured_output_demo.log   # JSON mode parsing & schema validation logs
│   ├── user_page_mockup.html        # Interactive HTML mockup of Diagnostic Hub UI
│   ├── user_page_overview.md        # Layout architecture breakdown
│   └── github_workflow_submission_guide.md # Assignment submission guide & video script
├── .env               # Local environment variables and API keys (git-ignored)
├── .env.example       # Example environment configuration template (committed)
├── .gitignore         # Version control exclusion rules
├── requirements.txt   # Python project dependencies (openai, python-dotenv, tiktoken)
├── WORKFLOW.md        # Team branching, commit conventions, PR process & onboarding guide
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

---

## 🏗️ Running Structured Output & Safe JSON Validation

To execute JSON mode extractions, test defensive JSON parsing (`safe_parse_json`), validate required schema keys (`validate_schema`), and test retry recovery:

```bash
python src/structured_output.py
```

### Key Learnings
- **Structured JSON Mode**: Enforces `response_format={"type": "json_object"}` alongside system prompt schema instructions (`{"answer": "...", "source_manual": "...", "confidence": 0.98}`).
- **Defensive Parsing (`safe_parse_json`)**: Gracefully handles markdown wrapping (` ```json `) and catches `JSONDecodeError` without application crashes.
- **Field & Type Validation (`validate_schema`)**: Ensures all required keys (`answer`, `source_manual`, `confidence`) exist and match expected types before returning data to the application.
- **Retry Recovery (`query_with_json_retry`)**: Automatically prompts the model once to fix syntax errors or supply missing keys if initial outputs fail validation.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).