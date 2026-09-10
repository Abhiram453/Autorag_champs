# Automotive RAG Assistant (`Autorag_champs`)

An AI-powered automotive diagnostic assistant that retrieves model-specific, up-to-date repair manuals, recall notices, and diagnostic guides for service centers across regions.

---

## ✨ Features

- **Upload documents**: Multi-format document intake (`.pdf`, `.txt`, `.md`, `.html`) with automated metadata extraction and file validation.
- **Ingest, chunk, embed, and index content**: Token-aware chunking, batch embedding generation (`text-embedding-3-small`), and vector similarity indexing.
- **Ask questions through a chat UI**: Interactive multi-portal web interface (`src/frontend`) and Streamlit workspace (`streamlit_app.py`) with real-time SSE streaming.
- **Receive grounded answers with citations**: Pre-generation quality guardrails and inline source attributions (`[1]`, `[2]`) mapped directly to document chunks.
- **View logs and usage summary**: Real-time token usage, per-query cost tracking, SHA-256 query caching, and structured JSON audit telemetry.

---

## 📁 Repository Structure

```
Autorag_champs/
├── .github/           # Issue and Pull Request templates
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/sprint_task.md
├── data/              # Source repair manuals, recall notices, diagnostic guides (.txt, .md, .html)
├── src/               # Application source code & RAG pipeline engines
│   ├── api_server.py                # FastAPI backend API server (/query, /status, /metrics, /audit-logs)
│   ├── conversational_rag.py        # Conversational RAG & query rewriting engine
│   ├── citation_generator.py        # Grounded generation with inline citations
│   ├── retrieval_guardrails.py      # Quality guardrails & similarity threshold gating
│   ├── hybrid_search.py             # Metadata-filtered & hybrid (semantic + lexical) search
│   ├── retrieval_tuner.py           # Retrieval quality tuning & benchmark evaluation engine
│   ├── batch_embedding_pipeline.py  # Batch embedding pipeline with backoff & resumable cache
│   ├── document_loader.py           # Multi-format document loader (.pdf, .txt, .md, .html)
│   ├── observability.py            # SHA-256 query caching, audit logging & token cost tracking
│   └── frontend/                    # 100% responsive multi-portal web client
│       ├── index.html               # Semantic HTML for all portal views
│       ├── style.css                # Glassmorphic automotive styling & responsive breakpoints
│       └── app.js                   # Routing, role switching, and live RAG API client
├── prompts/           # System prompt templates & persona instructions
│   ├── system_prompt.txt
│   ├── prompt_templates.py   # Vague vs. Strict System Prompts, Refusal Rules & JSON schemas
│   └── templates.py          # Centralized prompt templates with named placeholders & renderer
├── outputs/           # Logs, generated output artifacts, sample execution captures
│   ├── rag_api_test.log             # Automated FastAPI test suite logs
│   ├── conversational_rag_demo.log  # Conversational RAG & multi-turn query rewriting log
│   ├── guardrails_demo.log          # Retrieval strength guardrails & refusal gating log
│   ├── citation_generation_demo.log # Grounded LLM completion with citations log
│   ├── user_page_mockup.html        # Interactive HTML mockup of Diagnostic Hub UI
│   └── github_workflow_submission_guide.md # Assignment submission guide
├── tests/             # Automated test suite
│   ├── test_rag_api.py              # End-to-end FastAPI & query test suite
│   ├── test_rag_streaming.py        # SSE streaming endpoint test suite
│   └── test_rag_observability.py    # Observability, caching & token cost test suite
├── streamlit_app.py   # Streamlit companion application
├── .env               # Local environment variables and API keys (git-ignored)
├── .env.example       # Example environment configuration template (committed)
├── .gitignore         # Version control exclusion rules
├── requirements.txt   # Python dependencies (fastapi, uvicorn, streamlit, openai, etc.)
├── WORKFLOW.md        # Team branching, commit conventions, PR process & onboarding guide
└── README.md          # Project documentation
```

---

## ⚙️ Setup & Configuration

### 1. Install Dependencies
Create a virtual environment and install the required Python dependencies:
```bash
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Secrets and API credentials must **never** be committed to source control. Create a local `.env` file from the provided template:
```bash
cp .env.example .env
```

Documented required configuration values:
```ini
# OpenAI & Model Configuration
OPENAI_API_KEY=your_api_key_here
CHAT_MODEL=openai/gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Vector Database & Retrieval Configuration
VECTOR_DB_URL=http://localhost:6333
VECTOR_COLLECTION=automotive_manuals

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 3. Run the Backend API Server
Start the FastAPI server using Uvicorn:
```bash
uvicorn src.api_server:app --reload --port 8000
```
Or execute directly using Python:
```bash
python src/api_server.py
```
Backend API endpoints will be accessible at:
- **Root & Multi-Portal UI**: `http://localhost:8000/`
- **Swagger Interactive API Docs**: `http://localhost:8000/docs`
- **Metrics & Health**: `http://localhost:8000/metrics/observability`

### 4. Run the Frontend Chat UI
You can run the web portal client or the Streamlit workspace:

```bash
# Option A: Built-in Web Client (Static Web Server)
python -m http.server 3000 --directory src/frontend
# Access at http://localhost:3000

# Option B: Streamlit Companion App
streamlit run streamlit_app.py
# Access at http://localhost:8501
```

---

## 🔒 Configure Secrets Safely

Secrets are strictly protected from accidental version control commits via `.gitignore`:

```gitignore
.env
.env.local
*.pem
```

For local development, keep your actual secret API keys inside `.env` (which is excluded by `.gitignore`). For deployment (e.g., Vercel, Render, Railway, AWS), configure environment variables directly in the hosting provider's secret management settings rather than hardcoding them in source code.

---

## 🧪 End-to-End Demo

Uploaded document: `sample_manual.txt`

**Question:**
What is the primary resistance specification for Bank 1 ignition coils on DTC P0300?

**Answer:**
The primary resistance specification for Bank 1 ignition coils must measure 0.4 to 0.6 ohms across terminals 1 and 2. [1]

**Sources:**
```text
[1] sample_manual.txt, chunk chunk_mnl_001
"AUTOMOTIVE REPAIR MANUAL: DTC P0300 indicates random misfire. Inspect Bank 1 ignition coils. Primary resistance specification: 0.4 to 0.6 ohms across terminals 1 and 2."
```

This confirms that upload, ingestion, retrieval, generation, and citation display all work together seamlessly.

---

## 🛡️ Retrieval Quality Guardrails & Refusal Gating

To execute pre-generation retrieval strength checking (`MIN_TOP_SCORE = 0.70`), halt LLM invocation on weak/empty context (`status: "refused_weak_context"`), and preserve confident generation (`status: "answered"`) for supported queries:

```bash
python src/retrieval_guardrails.py
```

### Key Learnings
- **Pre-Generation Refusal Gating**: Evaluating similarity scores before calling the LLM prevents hallucinations when evidence is missing.
- **Threshold Control**: Queries with top similarity scores `< 0.70` trigger immediate refusal (*"I don't have enough reliable context to answer that."*) without wasting API tokens.
- **Confident Generation**: Queries with strong retrieved context (`>= 0.70`) proceed cleanly to grounded generation with inline citations.

---

## 💬 Conversational RAG & Query Rewriting

To execute multi-turn conversational RAG with automatic LLM query rewriting:

```bash
python src/conversational_rag.py
```

### Key Learnings
- **Query Reformulation Engine**: Rewrites follow-up questions (e.g. *"What connector should I inspect?"*) into self-contained standalone search queries (e.g. *"What connector should be inspected for misfire issues related to DTC P0300 on 2023 SUV Model X?"*).
- **Standalone Retrieval**: Vector search runs against the rewritten query to ensure accurate semantic matching across multi-turn sessions.
- **Grounded Responses & Safe Refusals**: Supported turns return citation-backed answers (`[1]`, `[2]`), while unsupported questions trigger guardrail refusals.

---

## 🧪 Running Automated Test Suite

Verify API endpoints, SSE streaming, guardrail gating, validation rules, and caching telemetry:

```bash
# REST API Test Suite
python tests/test_rag_api.py

# SSE Streaming RAG Test Suite
python tests/test_rag_streaming.py

# Observability, Caching & Cost Tracking Test Suite
python tests/test_rag_observability.py
```

---

## 📊 RAG Observability, Query Caching & Cost Tracking

- **SHA-256 Query Cache**: Deterministic hashes for instant repeated query response (`< 5ms`, `cache_hit: true`).
- **Structured JSON Audit Logging**: Logs request telemetry, tokens, latency, cost, and sources to `outputs/rag_observability.log`.
- **Token Accounting**: High-precision token calculation using `tiktoken` with character fallback.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).