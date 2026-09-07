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
├── src/               # Ingestion, document loading, chunking, embeddings, sanity testing, hybrid search, retrieval tuning, parameters, and history code
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
│   └── retrieval_tuner.py    # Retrieval quality tuning & empirical benchmark evaluation engine
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

## 📊 Running Retrieval Quality Tuning & Evaluation

To benchmark multiple retrieval configurations (`baseline_k3`, `filtered_k3`, `strict_threshold_k5`, `hybrid_threshold_k3`), calculate **Hit Rate** percentages, and empirically justify optimal retrieval settings:

```bash
python src/retrieval_tuner.py
```

### Key Learnings
- **Empirical Tuning**: Evaluating retrieval configurations against known test queries provides data-driven justification for production hyperparameter choices.
- **Hit Rate Metric**: Measures the percentage of test queries for which the expected target document appears in the retrieved results (100% achieved).
- **Score Thresholding**: Discarding low-confidence candidates (`min_score=0.60`) prevents context pollution and LLM hallucination.

---

## 🚀 Team Workflow & Guidelines

For team collaboration rules, per-assignment branching strategy (`feature/<name>`), conventional commit formats (`feat:`, `fix:`, `docs:`), Pull Request review checklists, issue tracking, and contributor onboarding, see [WORKFLOW.md](file:///d:/RAG/Autorag_champs/WORKFLOW.md).