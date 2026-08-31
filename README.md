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
│   ├── structured_output.py  # Defensive JSON mode parser, schema validator & retry recovery
│   └── prompt_template_engine.py # Multi-feature prompt template renderer & reusability engine
├── prompts/           # System prompt templates & persona instructions
│   ├── system_prompt.txt
│   ├── prompt_templates.py   # Vague vs. Strict System Prompts, Refusal Rules & JSON schemas
│   └── templates.py          # Centralized prompt templates with named placeholders & renderer
├── outputs/           # Logs, generated output artifacts, sample execution captures
│   ├── sample_output.txt
│   ├── prompt_comparison_results.log # Execution trace of side-by-side prompt tests
│   ├── token_cost_analysis.log      # Token counting, call costs & corpus scale budget
│   ├── history_management_demo.log  # Multi-turn history, trimming & summarization logs
│   ├── parameter_comparison_results.log # Generation parameters control test logs
│   ├── structured_output_demo.log   # JSON mode parsing & schema validation logs
│   ├── prompt_templates_demo.log    # Multi-feature prompt template rendering logs
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

## 📝 Running Prompt Templates & Reusability Experiments

To test centralized prompt template rendering with named placeholders (`{context}`, `{question}`, `{vehicle_model}`, `{dtc_code}`) and verify multi-feature reuse across chat endpoints, evaluators, and CLI tools:

```bash
python src/prompt_template_engine.py
```

### Key Learnings
- **Decoupled Architecture**: Prompts live in `prompts/templates.py`, completely separate from application business logic in `src/`.
- **Runtime Variable Injection**: Dynamic placeholders (`{context}`, `{question}`) are injected cleanly using `render_prompt(template, **values)`.
- **Multi-Feature Reuse**: A single prompt template (`RAG_ANSWER_TEMPLATE`) powers 3 separate features (Web Chat, Batch Evaluator, CLI Tool), guaranteeing zero prompt drift.
- **Single-Point Updates**: Grounding rules or citation instructions are edited once in `prompts/templates.py` and instantly update all 3 features.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).