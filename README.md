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
│   └── parameter_experiment.py # Generation parameters control (temperature, max_tokens, stop)
├── src/               # Ingestion, embedding, retrieval, and history management code
│   ├── chat_completion.py    # OpenAI-compatible API client & chat completion handler
│   ├── prompt_experiment.py  # Side-by-side prompt engineering experiment runner
│   ├── token_estimator.py    # Token counter, cost calculator & corpus scale estimator
│   └── history_manager.py    # Multi-turn conversation manager, FIFO trimming & summarization
├── prompts/           # System prompt templates & persona instructions
│   ├── system_prompt.txt
│   └── prompt_templates.py   # Vague vs. Strict System Prompts, Refusal Rules & JSON schemas
├── outputs/           # Logs, generated output artifacts, sample execution captures
│   ├── sample_output.txt
│   ├── prompt_comparison_results.log # Execution trace of side-by-side prompt tests
│   ├── token_cost_analysis.log      # Token counting, call costs & corpus scale budget
│   ├── history_management_demo.log  # Multi-turn history, trimming & summarization logs
│   ├── parameter_comparison_results.log # Generation parameters control test logs
│   ├── user_page_mockup.html        # Interactive HTML mockup of Diagnostic Hub UI
│   ├── user_page_overview.md        # Layout architecture breakdown
│   └── github_workflow_submission_guide.md # Assignment submission guide & video script
│   ├── user_page_mockup.html        # Interactive HTML mockup of Diagnostic Hub UI
│   ├── user_page_overview.md        # Layout architecture breakdown
│   └── github_workflow_submission_guide.md # Assignment 3.11 submission guide & video script
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

## 🎛️ Running Generation Parameters Control Experiments

To test generation parameters (`temperature`, `max_tokens`, `stop`, `top_p`) and verify deterministic factual RAG configurations:

```bash
python src/parameter_experiment.py
```

### Key Learnings
- **`temperature` (0.0 – 2.0)**: Low settings (`0.0 - 0.2`) produce deterministic, repeatable factual answers across runs. High settings (`1.0`) introduce variability and risk embellishment.
- **`max_tokens`**: Caps maximum completion length, enforcing output bounds and controlling token costs.
- **`stop` Sequences**: Terminates generation early (e.g. `stop=["\n\n2.", "Step 2:"]`) to prevent model rambling.
- **Recommended Grounded RAG Preset**: `temperature=0.1`, `max_tokens=250`, `stop=["\n\n"]`.
## 💬 Running Multi-Turn History & Context Trimming

To test multi-turn conversation history tracking, token budget monitoring, FIFO trimming (`messages.pop(1)`), and LLM summarization strategies across 6–10 diagnostic turns:

```bash
python src/history_manager.py
```

### Key Learnings
- **The Context Window Budget**: As multi-turn diagnostic chats progress, accumulated user/assistant turns compete for token space alongside system prompts and retrieved manual chunks.
- **FIFO Trimming Strategy**: Automatically drops the oldest non-system turns (`messages.pop(1)`) when payload tokens exceed the set budget (e.g. 180 tokens in demo), protecting the root system prompt at index 0.
- **Summarization Strategy**: Condenses older conversation turns into a single `[CONVERSATION SUMMARY]` block, maintaining core vehicle context (DTC P0300, VIN, Bank 1 specs) while reducing token footprint.
- **Trade-off Balance**: More history = better continuity but higher cost and overflow risk; Less history (trimmed) = lower cost and safer execution but potential loss of early conversation details.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).
For team collaboration rules, branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).
