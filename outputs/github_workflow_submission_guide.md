# Autorag Champs — Per-Assignment Branching, Commits & PR Guide

This guide details the **per-assignment branching strategy** for `https://github.com/Abhiram453/Autorag_champs`. Each assignment has its own dedicated feature branch, issue linkage, commit history, and Pull Request (PR).

---

## 📌 Assignment 1: Workspace & API Setup (`src/chat_completion.py`)
- **Branch**: `feature/api-setup-chat-completion`
- **PR Title**: `feat: Setup OpenAI-compatible chat completion client with environment config and 401/429 error handling`
- **Related Issue**: `Closes #1`

### 1. Git Commands
```bash
git checkout main
git checkout -b feature/api-setup-chat-completion
git add requirements.txt .gitignore .env.example src/chat_completion.py outputs/sample_output.txt README.md
git commit -m "feat: implement OpenAI-compatible API chat completion client with error handling"
git push -u origin feature/api-setup-chat-completion
```

### 2. GitHub PR Details
- **Source Branch**: `feature/api-setup-chat-completion` -> **Base Branch**: `main`
- **PR Title**: `feat: Setup OpenAI-compatible chat completion client with environment config and 401/429 error handling`
- **PR Description Body**:
  ```markdown
  ## Summary
  Configures environment loading via python-dotenv, structured logging, token usage tracking, and 401/429 error handling for the API client.

  ## Related Issue
  Closes #1
  ```
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/1`

---

## 📌 Assignment 2: Prompt Engineering & System vs User Constraints (`src/prompt_experiment.py`)
- **Branch**: `feature/prompt-engineering-constraints`
- **PR Title**: `feat: Add side-by-side prompt engineering runner with refusal rules and JSON format schemas`
- **Related Issue**: `Closes #2`

### 1. Git Commands
```bash
git checkout main
git checkout -b feature/prompt-engineering-constraints
git add prompts/prompt_templates.py src/prompt_experiment.py outputs/prompt_comparison_results.log README.md
git commit -m "feat: implement side-by-side prompt engineering experiments and refusal rules"
git push -u origin feature/prompt-engineering-constraints
```

### 2. GitHub PR Details
- **Source Branch**: `feature/prompt-engineering-constraints` -> **Base Branch**: `main`
- **PR Title**: `feat: Add side-by-side prompt engineering runner with refusal rules and JSON format schemas`
- **PR Description Body**:
  ```markdown
  ## Summary
  Implements prompt engineering templates comparing vague vs. strict system prompts, refusal rules ("I don't know based on available service data"), and strict JSON output schemas.

  ## Related Issue
  Closes #2
  ```
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/2`

---

## 📌 Assignment 3: Tokenization & Cost Estimation Engine (`src/token_estimator.py`)
- **Branch**: `feature/token-counting-cost-estimation`
- **PR Title**: `feat: Add token counting engine, per-call cost estimator, and 4,000-document corpus scale budget`
- **Related Issue**: `Closes #3`

### 1. Git Commands
```bash
git checkout main
git checkout -b feature/token-counting-cost-estimation
git add requirements.txt src/token_estimator.py outputs/token_cost_analysis.log README.md
git commit -m "feat: implement token counting with tiktoken, API call cost calculation, and 4000-doc corpus budgeting"
git push -u origin feature/token-counting-cost-estimation
```

### 2. GitHub PR Details
- **Source Branch**: `feature/token-counting-cost-estimation` -> **Base Branch**: `main`
- **PR Title**: `feat: Add token counting engine, per-call cost estimator, and 4,000-document corpus scale budget`
- **PR Description Body**:
  ```markdown
  ## Summary
  Adds token counting via tiktoken (cl100k_base), API call cost calculations, RAG context window budgeting, and corpus-scale ingestion estimates for 4,000 repair manuals.

  ## Related Issue
  Closes #3
  ```
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/3`

---

## 📌 Assignment 4: Conversation History & Context Trimming (`src/history_manager.py`)
- **Branch**: `feature/conversation-history-management`
- **PR Title**: `feat: Add multi-turn conversation history manager with FIFO trimming and summarization strategies`
- **Related Issue**: `Closes #4`
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/4`

---

## 📌 Assignment 5: Generation Parameters Control (`src/parameter_experiment.py`)

### 1. Git Commands
```bash
git checkout main
git checkout -b feature/generation-parameters-control
git add src/parameter_experiment.py outputs/parameter_comparison_results.log README.md
git commit -m "feat: implement generation parameters control runner for temperature, max_tokens, and stop sequences"
git push -u origin feature/generation-parameters-control
```

### 2. GitHub PR Details
- **Source Branch**: `feature/generation-parameters-control` -> **Base Branch**: `main`
- **PR Title**: `feat: Add generation parameters control experiments for temperature, max_tokens, and stop sequences`
- **PR Description Body**:
  ```markdown
  ## Summary
  Implements parameter experiment engine testing temperature determinism (0.0 vs 1.0), max_tokens cost caps, and stop sequence early termination for grounded RAG.

  ## Related Issue
  Closes #6
  ```
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/6`
git checkout -b feature/conversation-history-management
git add src/history_manager.py outputs/history_management_demo.log README.md
git commit -m "feat: implement multi-turn conversation history manager with FIFO trimming and LLM summarization"
git push -u origin feature/conversation-history-management
```

### 2. GitHub PR Details
- **Source Branch**: `feature/conversation-history-management` -> **Base Branch**: `main`
- **PR Title**: `feat: Add multi-turn conversation history manager with FIFO trimming and summarization strategies`
- **PR Description Body**:
  ```markdown
  ## Summary
  Implements multi-turn history tracking, token budget monitoring, FIFO trimming (messages.pop(1)), and LLM summarization to prevent context overflow in long chat sessions.

  ## Related Issue
  Closes #4
  ```
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/4`

---

## 📌 Assignment 3.11: GitHub Team Workflow Setup (`WORKFLOW.md`)
- **Branch**: `feature/github-workflow-setup`
- **PR Title**: `docs: Add team GitHub workflow documentation and contributor guidelines`
- **Related Issue**: `Closes #5`

### 1. Git Commands
```bash
git checkout main
git checkout -b feature/github-workflow-setup
git add WORKFLOW.md .github/ README.md outputs/github_workflow_submission_guide.md
git commit -m "docs: document team github workflow and conventions"
git push -u origin feature/github-workflow-setup
```

### 2. GitHub PR Details
- **Source Branch**: `feature/github-workflow-setup` -> **Base Branch**: `main`
- **PR Title**: `docs: Add team GitHub workflow documentation and contributor guidelines`
- **PR Description Body**:
  ```markdown
  ## Summary
  Establishes team branching strategy, conventional commit standards, PR review checklists, issue tracking, and contributor onboarding guide in WORKFLOW.md.

  ## Related Issue
  Closes #5
  ```
- **PR Link Format**: `https://github.com/Abhiram453/Autorag_champs/pull/5`
