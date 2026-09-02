# Aura Automotive RAG Assistant - Team GitHub Workflow & Guidelines

This document defines the team collaboration standards, per-assignment branching strategy, conventional commit conventions, code review process, issue tracking methodology, and onboarding instructions for the `Autorag_champs` repository (`https://github.com/Abhiram453/Autorag_champs`).

---

## 🌿 1. Per-Assignment Branching Strategy

To maintain complete auditability and fulfill assignment submission requirements, **every single assignment/concept must have its own dedicated feature branch and open Pull Request (PR)**. Direct commits to the `main` branch are strictly prohibited.

### Assignment Branch Naming Map
| Assignment / Concept Module | Dedicated Branch Name | Key Files |
| :--- | :--- | :--- |
| **Concept 1: Workspace & API Setup** | `feature/api-setup-chat-completion` | `src/chat_completion.py`, `.env.example`, `requirements.txt` |
| **Concept 2: Prompt Engineering & Constraints** | `feature/prompt-engineering-constraints` | `prompts/prompt_templates.py`, `src/prompt_experiment.py` |
| **Concept 3: Tokenization & Cost Estimation** | `feature/token-counting-cost-estimation` | `src/token_estimator.py`, `outputs/token_cost_analysis.log` |
| **Concept 4: History & Context Trimming** | `feature/conversation-history-management` | `src/history_manager.py`, `outputs/history_management_demo.log` |
| **Concept 5: Generation Parameters Control** | `feature/generation-parameters-control` | `src/parameter_experiment.py`, `outputs/parameter_comparison_results.log` |
| **Concept 6: Structured Output & JSON Parsing** | `feature/structured-output-json-validation` | `src/structured_output.py`, `outputs/structured_output_demo.log` |
| **Concept 7: Prompt Templates & Reusability** | `feature/prompt-templates-reusability` | `prompts/templates.py`, `src/prompt_template_engine.py` |
| **Concept 10: Document Loading & Intake** | `feature/document-loading-intake` | `src/document_loader.py`, `data/`, `outputs/document_intake_summary.log` |
| **Concept 11: Scalable Batch Embedding Pipeline** | `feature/scalable-batch-embedding-pipeline` | `src/batch_embedding_pipeline.py`, `outputs/batch_embeddings_cache.json` |
| **Concept 17: Embedding Sanity Testing** | `feature/embedding-sanity-testing` | `src/embedding_sanity_test.py`, `outputs/embedding_sanity_report.log` |
| **Assignment 3.11: GitHub Team Workflow** | `feature/github-workflow-setup` | `WORKFLOW.md`, `.github/`, `README.md` |

- **Branch Lifecycle**:
  For each assignment:
  1. Create a fresh branch from `main`: `git checkout -b feature/<assignment-name>`.
  2. Commit using Conventional Commits (`feat:`, `docs:`, `chore:`).
  3. Push branch to GitHub: `git push -u origin feature/<assignment-name>`.
  4. Open a Pull Request targeting `main` containing `Closes #<issue_number>`.
  5. Keep PR open for evaluation/submission.

---

## ✍️ 2. Commit Message Conventions

We enforce the **Conventional Commits** specification (`type: description`).

### Allowed Types
- **`feat`**: A new feature or capability.
- **`fix`**: A bug fix or correction.
- **`docs`**: Documentation updates only.
- **`refactor`**: Code cleanup without changing behavior.
- **`chore`**: Maintenance tasks, dependency updates, or environment configs.

---

## 🔍 3. Pull Request (PR) & Code Review Process

Every assignment submission requires an open Pull Request on GitHub:
1. Open PR from `feature/<assignment-name>` targeting `main`.
2. Title format: `feat: <Assignment Title / Capability>`.
3. Include `Closes #<issue_number>` in the PR description body.
