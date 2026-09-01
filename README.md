# Automotive RAG Assistant (`Autorag_champs`)

An AI-powered automotive diagnostic assistant that retrieves model-specific, up-to-date repair manuals, recall notices, and diagnostic guides for service centers across regions.

---

## 📁 Repository Structure

```
Autorag_champs/
├── .github/           # Issue and Pull Request templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/sprint_task.md
├── data/              # Source repair manuals, recall notices, diagnostic guides (.txt, .md, .html, .pdf)
│   ├── sample_manual.txt  # Plain text repair manual for DTC P0300
│   ├── tsb_notice.md      # Markdown Technical Service Bulletin TSB-22-112
│   └── recall_report.html # HTML recall report for SUV Model X battery safety
├── src/               # Ingestion, document loading, embedding, retrieval, and history code
│   ├── chat_completion.py    # OpenAI-compatible API client & chat completion handler
│   ├── prompt_experiment.py  # Side-by-side prompt engineering experiment runner
│   ├── token_estimator.py    # Token counter, cost calculator & corpus scale estimator
│   ├── history_manager.py    # Multi-turn conversation manager, FIFO trimming & summarization
│   ├── parameter_experiment.py # Generation parameters control (temperature, max_tokens, stop)
│   ├── structured_output.py  # Defensive JSON mode parser, schema validator & retry recovery
│   ├── prompt_template_engine.py # Multi-feature prompt template renderer & reusability engine
│   └── document_loader.py    # Multi-format document loader (.pdf, .txt, .md, .html) & intake scanner
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
│   ├── document_intake_summary.log  # Multi-format document intake & metadata logs
│   ├── user_page_mockup.html        # Interactive HTML mockup of Diagnostic Hub UI
│   ├── user_page_overview.md        # Layout architecture breakdown
│   └── github_workflow_submission_guide.md # Assignment submission guide & video script
├── .env               # Local environment variables and API keys (git-ignored)
├── .env.example       # Example environment configuration template (committed)
├── .gitignore         # Version control exclusion rules
├── requirements.txt   # Python dependencies (openai, python-dotenv, tiktoken, pypdf, bs4)
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

## 📄 Running Document Loading & Multi-Format Intake

To execute multi-format document intake (`.pdf`, `.txt`, `.md`, `.html`), track source identity metadata (`source`), handle corrupt/unreadable files without pipeline crashes, and inspect character lengths and text previews:

```bash
python src/document_loader.py
```

### Key Learnings
- **Unified Text Form**: Embeddings and models require plain text. `.pdf` files are parsed via `pypdf`, `.txt`/`.md` via UTF-8 text readers, and `.html` via `BeautifulSoup` tag stripping.
- **Source Metadata Tracking**: Every ingested text snippet carries its `source` (filename / relative path) so retrieved answers can cite exact manuals.
- **Error-Resilient Pipeline**: Corrupt, unreadable, or scanned PDFs are caught gracefully with `try/except` logging without crashing the intake process across 4,000 files.
- **Intake Verification**: Inspects character counts and text previews (`text[:60]`) to confirm clean ingestion before chunking or embedding.

---

## ✂️ Document Chunking

Before embedding, documents must be split into **chunks** — the unit the retrieval system searches over. Chunk size controls the trade-off between retrieval precision, cost, and context quality.

### Running the Chunking Comparison

```bash
python src/chunking_comparison.py
```

This produces:
- `outputs/chunking_comparison.log` — per-document and corpus-wide stats for both strategies
- `outputs/sample_chunks.json` — first 3 chunks per strategy per document for boundary inspection

### Strategies Compared

| Strategy | Description | Config |
|---|---|---|
| **Fixed-Size with Overlap** | Splits text into 500-char windows with 100-char overlap | `chunk_size=500, overlap=100` |
| **Section-Based (Semantic)** | Splits on structural headers (`# Heading`, `1. SECTION TITLE`) with short-section merging | `min_section_len=100` |

### Corpus-Wide Chunk Stats

|  | Fixed-Size | Section-Based |
|---|---|---|
| **Total chunks** | 8 | 7 |
| **Avg chunk size** | 360.2 chars | 350.4 chars |
| **Min chunk size** | 25 chars | 149 chars |
| **Max chunk size** | 500 chars | 698 chars |

### Chosen Strategy: Section-Based

**Why it fits this corpus:**

1. **Structural integrity** — Repair manuals, TSBs, and recall notices use numbered sections. Section-based splitting keeps each procedure self-contained.
2. **Retrieval precision** — A query like *"How do I inspect connector C102?"* returns the complete service action, not a fragment cut at an arbitrary 500-char boundary.
3. **No tiny fragments** — Fixed-size chunking produced a 25-char chunk (`"or seals prior to mating."`) that is useless for retrieval. Section-based merging prevents this.
4. **Context window fit** — Section chunks (~150–700 chars, ~40–175 tokens) are compact enough to stack 3–5 in a single prompt alongside the system prompt and user query.

### How Chunk Size Relates to the Context Window

The **context window** is the model's total token budget per API call (e.g. 4K, 8K, 128K tokens). Every retrieved chunk consumes part of that budget. Smaller chunks allow more diverse evidence but may lack context; larger chunks provide richer context but fewer can fit. The ideal chunk size lets multiple relevant chunks + system prompt + user query fit comfortably within the window.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](WORKFLOW.md).