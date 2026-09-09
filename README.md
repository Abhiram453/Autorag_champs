# Automotive RAG Assistant (`Autorag_champs`)

An AI-powered automotive diagnostic assistant that retrieves model-specific, up-to-date repair manuals, recall notices, and diagnostic guides for service centers across regions.

---

## 📁 Repository Structure

```
Autorag_champs/
├── .github/           # Issue and Pull Request templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/sprint_task.md
├── data/              # Source repair manuals, recall notices, diagnostic guides (.txt, .md, .html)
├── src/               # Ingestion, document loading, chunking, embeddings, sanity testing, hybrid search, retrieval tuning, citations, guardrails, parameters, and history code
│   ├── chat_completion.py    # OpenAI-compatible API client & chat completion handler
│   ├── prompt_experiment.py  # Side-by-side prompt engineering experiment runner
│   ├── token_estimator.py    # Token counter, cost calculator & corpus scale estimator
│   ├── history_manager.py    # Multi-turn conversation manager, FIFO trimming & summarization
│   ├── parameter_experiment.py # Generation parameters control (temperature, max_tokens, stop)
│   ├── structured_output.py  # Defensive JSON mode parser, schema validator & retry recovery
│   ├── prompt_template_engine.py # Multi-feature prompt template renderer & reusability engine
│   ├── document_loader.py    # Multi-format document loader (.pdf, .txt, .md, .html) & intake scanner
│   ├── batch_embedding_pipeline.py # Scalable batch embedding pipeline with backoff & resumable cache
│   ├── embedding_sanity_test.py # Retrieval quality & embedding sanity testing engine
│   ├── hybrid_search.py      # Metadata-filtered & hybrid (semantic + lexical) search engine
│   ├── retrieval_tuner.py    # Retrieval quality tuning & empirical benchmark evaluation engine
│   ├── citation_generator.py # Grounded generation with inline citations & source attribution
│   ├── retrieval_guardrails.py # Pre-generation retrieval quality guardrails & refusal gating
│   └── conversational_rag.py # Conversational RAG engine with LLM query rewriting & multi-turn history
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
│   ├── batch_embeddings_cache.json  # Persistent vector cache for idempotent resumption
│   ├── batch_embedding_pipeline_summary.log # Batch embedding & cost tracking log
│   ├── embedding_sanity_report.log  # Retrieval relevance & sanity test report
│   ├── hybrid_search_comparison.log # Side-by-side filtered & hybrid search comparison log
│   ├── retrieval_tuning_results.log # Benchmark evaluation & Hit Rate tuning log
│   ├── citation_generation_demo.log # Grounded LLM completion with citations log
│   ├── guardrails_demo.log          # Retrieval strength guardrails & refusal gating log
│   ├── conversational_rag_demo.log  # Conversational RAG & multi-turn query rewriting log
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

## 🛡️ Running Retrieval Quality Guardrails

To execute pre-generation retrieval strength checking (`MIN_TOP_SCORE = 0.70`), halt LLM invocation on weak/empty context (`status: "refused_weak_context"`), and preserve confident generation (`status: "answered"`) for supported queries:

```bash
python src/retrieval_guardrails.py
```

### Key Learnings
- **Pre-Generation Refusal Gating**: Evaluating similarity scores before calling the LLM prevents the model from hallucinating plausible-sounding answers when evidence is missing.
- **Threshold Control**: Queries with top similarity scores `< 0.70` trigger immediate refusal (*"I don't have enough reliable context to answer that."*) without wasting API tokens.
- **Confident Generation**: Queries with strong retrieved context (`>= 0.70`) proceed cleanly to grounded generation with inline citations.

---

## 💬 Running Conversational RAG & Query Rewriting

To execute multi-turn conversational RAG with automatic LLM query rewriting and retrieval guardrails:

```bash
python src/conversational_rag.py
```

### Key Learnings
- **Query Reformulation Engine**: Conversational follow-ups (e.g. *"What connector should I inspect?"*) are rewritten into self-contained standalone search queries (e.g. *"What connector should be inspected for misfire issues related to DTC P0300 on 2023 SUV Model X?"*) using prior dialogue context.
- **Standalone Retrieval & Guardrails**: Vector search runs against the rewritten query to ensure accurate semantic matching and prevent context drift across multi-turn sessions.
- **Grounded Responses & Safe Refusals**: Supported turns return citation-backed answers (`[1]`, `[2]`), while out-of-domain or under-supported follow-ups trigger guardrail refusals.

## 📤 Uploading and Indexing Documents at Runtime

Start the API from the repository root:

```bash
uvicorn src.api:app --reload --port 8000
```

Upload a supported `.txt`, `.md`, `.pdf`, `.html`, or `.htm` document. The API stores it under `data/uploads/` with a generated safe filename, extracts and cleans its text, chunks it, embeds every chunk, and appends the vectors to the running RAG engine without a restart:

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
	-F "file=@data/new_service_notice.txt"
```

The response reports `chunks_indexed`, `vector_dimensions`, and `index_status: "searchable immediately"`. Query the new material through the existing `/api/v1/query` endpoint. Empty files return `400`, unsupported extensions return `400`, files over 10 MB return `413`, unreadable documents return `422`, and embedding/indexing failures return `502`.

See [docs/upload_sample_run.md](docs/upload_sample_run.md) for a reproducible request, indexing summary, and follow-up query evidence.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).