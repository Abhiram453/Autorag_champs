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
├── src/               # Ingestion, embedding, retrieval, and chat completion code
│   └── chat_completion.py  # OpenAI-compatible API client & chat completion handler
├── prompts/           # System prompt templates & persona instructions
│   └── system_prompt.txt
├── outputs/           # Logs, generated output artifacts, sample execution captures
│   ├── sample_output.txt
│   └── github_workflow_submission_guide.md # Assignment 3.11 submission guide & video script
├── .env               # Local environment variables and API keys (git-ignored)
├── .env.example       # Example environment configuration template (committed)
├── .gitignore         # Version control exclusion rules
├── requirements.txt   # Python project dependencies
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
Edit `.env`:
```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_actual_api_key_here
CHAT_MODEL=gpt-4o-mini
```

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).

For Assignment 3.11 submission templates, PR copy-paste text, issue formats, and the 5-minute video script, see [outputs/github_workflow_submission_guide.md](file:///d:/RAG/Autorag_champs/outputs/github_workflow_submission_guide.md).