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
│   ├── rag_api_test.log             # Automated FastAPI test suite logs
│   ├── conversational_rag_demo.log  # Conversational RAG & multi-turn query rewriting log
│   ├── user_page_mockup.html        # Interactive HTML mockup of Diagnostic Hub UI
│   ├── user_page_overview.md        # Layout architecture breakdown
│   └── github_workflow_submission_guide.md # Assignment submission guide & video script
├── src/               # Application source code
│   ├── api_server.py                # FastAPI backend API server (/query, /status, /metrics, /audit-logs)
│   ├── conversational_rag.py        # Conversational RAG & query rewriting engine
│   ├── citation_generator.py        # Grounded generation with inline citations
│   ├── retrieval_guardrails.py      # Quality guardrails & similarity threshold gating
│   └── frontend/                    # 100% responsive multi-portal web client
│       ├── index.html               # Semantic HTML for all 4 portal views
│       ├── style.css                # Glassmorphic automotive styling & responsive breakpoints
│       └── app.js                   # Routing, role switching, and live RAG API client
├── tests/             # Automated test suite
│   └── test_rag_api.py              # End-to-end FastAPI & query test suite
├── streamlit_app.py   # Streamlit companion application with st.chat and st.status
├── .env               # Local environment variables and API keys (git-ignored)
├── .env.example       # Example environment configuration template (committed)
├── .gitignore         # Version control exclusion rules
├── requirements.txt   # Python dependencies (fastapi, uvicorn, streamlit, openai, etc.)
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

## 🌐 Running the Multi-Portal Platform & Diagnostic Hub UI

The platform provides a 100% responsive interface with three secure portals:
- **Technician Portal (`Diagnostic Hub`)**: Live RAG Chat (`POST /query`), VIN search, DTC detection (`P0300`), specs table, inline citations `[1]`, `[2]`, verified source drawer, and step-by-step repair instruction viewer.
- **Manager Portal (`Command Center`)**: Management oversight, operational metrics (`1,248` repairs, `78%` recalls, `42` pending approvals), recent activity feed, and SUV recall compliance tracking.
- **Admin Portal (`Knowledge Base & Audit Panel`)**: Document upload drag-and-drop zone, metadata tagging form (Model, Year, Region, Version, Status), document library table, and global compliance audit logs with technician feedback trends.

### Option A: Running the FastAPI Web Application
Start the FastAPI server:
```bash
python -m uvicorn src.api_server:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to:
- **Interactive Multi-Portal UI**: `http://127.0.0.1:8000/`
- **Swagger Interactive API Docs**: `http://127.0.0.1:8000/docs`

### Option B: Running the Streamlit Companion App
Start Streamlit:
```bash
streamlit run streamlit_app.py
```

### Running Automated Test Suite
To verify all API endpoints, SSE streaming protocol, guardrail gating, validation rules, and frontend delivery:
```bash
# REST API Test Suite
python tests/test_rag_api.py

# SSE Streaming RAG Test Suite
python tests/test_rag_streaming.py

# Observability, Caching & Cost Tracking Test Suite
python tests/test_rag_observability.py
```

---

## ⚡ Streaming RAG with Progressive Citations

The system connects a streaming backend (`POST /query/stream`) to the chat interface using Server-Sent Events (`text/event-stream`):
1. **Low Latency & High Perceived Speed**: The LLM streams answer tokens progressively as they are generated, rather than forcing the user to wait for the complete response.
2. **Citations-First Architecture**: Retrieved evidence is emitted as a typed `citations` event before the first token arrives, allowing users to inspect grounding sources immediately via `<details>` and `<summary>` tabs.
3. **Graceful Interruption & Error Handling**: If a stream is interrupted by network failure or backend timeout, partial output is preserved with an `(Incomplete)` badge, received citations remain visible, and an inline `Retry` button enables resuming.

---

## 📊 RAG Observability, Query Caching & Cost Tracking

A robust RAG system must be observable, cost-conscious, and auditable. Concept 34 introduces:
1. **SHA-256 Query Cache with TTL**:
   - Computes deterministic SHA-256 hashes of normalized, lowercase questions and filter sets.
   - Repeated queries return in `< 5ms` with zero token spend and `cache_hit: true`.
   - Built-in 15-minute Time-To-Live (TTL) automatically purges stale cached responses.
   - Flush endpoint `POST /cache/clear` allows manual or automated cache eviction.
2. **Structured JSON Audit Logging**:
   - Emits standardized JSON lines to `outputs/rag_observability.log` on every request.
   - Captures `timestamp`, `request_id`, `question`, `answer_preview`, `sources`, `cache_hit`, `input_tokens`, `output_tokens`, `total_tokens`, `estimated_cost`, `latency_ms`, and `status`.
3. **Token Usage & Cost Accounting**:
   - High-precision token calculation using `tiktoken` with fallback character estimation.
   - Transparent pricing model: `$0.00015 / 1k` input tokens and `$0.00060 / 1k` output tokens.
4. **Operational Metrics & Monitoring**:
   - `GET /metrics/observability`: Exposes aggregated telemetry (`total_requests`, `cache_hits`, `cache_hit_rate`, `total_estimated_cost`, `average_latency_ms`, `total_tokens_spent`, `active_cache_entries`).
   - Generates monitoring reports via `generate_usage_report()` saved to `outputs/observability_summary.json`.
   - Multi-portal UI visibility: Technician Hub displays `⚡ Cached (0ms • $0.00)` or `🧠 Live RAG (tokens • cost)` badges, while Manager Command Center visualizes real-time Cache Hit Rate %, Total Spend ($), and Avg Latency.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).