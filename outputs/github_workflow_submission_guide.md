# Autorag Champs — Per-Assignment Branching, Commits & PR Guide

This guide details the **per-assignment branching strategy** for `https://github.com/Abhiram453/Autorag_champs`. Each assignment has its own dedicated feature branch, issue linkage, commit history, and Pull Request (PR).

---

## 📌 Assignment 1: Workspace & API Setup (`src/chat_completion.py`)
- **Branch**: `feature/api-setup-chat-completion`
- **PR Title**: `feat: Setup OpenAI-compatible chat completion client with environment config and 401/429 error handling`
- **Related Issue**: `Closes #1`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/1`

---

## 📌 Assignment 2: Prompt Engineering & System vs User Constraints (`src/prompt_experiment.py`)
- **Branch**: `feature/prompt-engineering-constraints`
- **PR Title**: `feat: Add side-by-side prompt engineering runner with refusal rules and JSON format schemas`
- **Related Issue**: `Closes #2`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/2`

---

## 📌 Assignment 3: Tokenization & Cost Estimation Engine (`src/token_estimator.py`)
- **Branch**: `feature/token-counting-cost-estimation`
- **PR Title**: `feat: Add token counting engine, per-call cost estimator, and 4,000-document corpus scale budget`
- **Related Issue**: `Closes #3`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/3`

---

## 📌 Assignment 4: Conversation History & Context Trimming (`src/history_manager.py`)
- **Branch**: `feature/conversation-history-management`
- **PR Title**: `feat: Add multi-turn conversation history manager with FIFO trimming and summarization strategies`
- **Related Issue**: `Closes #4`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/4`

---

## 📌 Assignment 5: Generation Parameters Control (`src/parameter_experiment.py`)
- **Branch**: `feature/generation-parameters-control`
- **PR Title**: `feat: Add generation parameters control experiments for temperature, max_tokens, and stop sequences`
- **Related Issue**: `Closes #6`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/6`

---

## 📌 Assignment 6: Structured Output & JSON Parsing (`src/structured_output.py`)
- **Branch**: `feature/structured-output-json-validation`
- **PR Title**: `feat: Add structured JSON output mode, defensive parser, schema validator, and retry recovery`
- **Related Issue**: `Closes #7`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/7`

---

## 📌 Assignment 7: Prompt Templates & Reusability (`src/prompt_template_engine.py`)
- **Branch**: `feature/prompt-templates-reusability`
- **PR Title**: `feat: Add decoupled prompt templates directory, placeholder renderer, and multi-feature engine`
- **Related Issue**: `Closes #8`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/8`

---

## 📌 Assignment 10: Document Loading & Multi-Format Intake (`src/document_loader.py`)
- **Branch**: `feature/document-loading-intake`
- **PR Title**: `feat: Add multi-format document loader for PDF, TXT, HTML, and MD with error-resilient intake`
- **Related Issue**: `Closes #9`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/9`

---

## 📌 Assignment 11: Scalable Batch Embedding Pipeline (`src/batch_embedding_pipeline.py`)
- **Branch**: `feature/scalable-batch-embedding-pipeline`
- **PR Title**: `feat: Add scalable batch embedding pipeline with exponential backoff retry and idempotent caching`
- **Related Issue**: `Closes #10`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/10`

---

## 📌 Assignment 17: Embedding Sanity Testing (`src/embedding_sanity_test.py`)

### 1. Git Commands
```bash
git checkout main
git checkout -b feature/embedding-sanity-testing
git add src/embedding_sanity_test.py outputs/embedding_sanity_report.log README.md
git commit -m "feat: implement embedding sanity testing suite, cosine similarity ranker, and failure case analyzer"
git push -u origin feature/embedding-sanity-testing
```

### 2. GitHub PR Details
- **Source Branch**: `feature/embedding-sanity-testing` -> **Base Branch**: `main`
- **PR Title**: `feat: Add embedding sanity testing suite, cosine similarity ranking, and failure case analyzer`
- **PR Description Body**:
  ```markdown
  ## Summary
  Implements embedding sanity testing suite (src/embedding_sanity_test.py) using known query-chunk test cases, cosine similarity ranking, edge case failure analysis, and structured sanity reporting.

  ## Related Issue
  Closes #17
  ```
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/17`

---

## 📌 Assignment 3.11: GitHub Team Workflow Setup (`WORKFLOW.md`)
- **Branch**: `feature/github-workflow-setup`
- **PR Title**: `docs: Add team GitHub workflow documentation and contributor guidelines`
- **Related Issue**: `Closes #5`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/5`
