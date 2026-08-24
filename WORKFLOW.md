# Aura Automotive RAG Assistant - Team GitHub Workflow & Guidelines

This document defines the team collaboration standards, branching strategy, commit conventions, code review process, issue tracking methodology, and onboarding instructions for the `Autorag_champs` repository (`https://github.com/Abhiram453/Autorag_champs`).

---

## 🌿 1. Team Branching Strategy

To maintain pipeline stability and prevent merge conflicts, direct commits to the `main` branch are strictly prohibited.

- **Main Branch (`main`)**: Holds production-ready, fully tested, and releasable code only.
- **Feature & Task Branches**: All development work occurs in isolated short-lived feature branches branching off `main`.
- **Branch Naming Conventions**:
  Branch names must follow the pattern `<type>/<short-kebab-description>`:
  - `feature/<description>`: New features or capabilities (e.g., `feature/data-ingestion`, `feature/diagnostic-rag-engine`).
  - `fix/<description>`: Bug fixes or corrections (e.g., `fix/validation-logic`, `fix/token-counter`).
  - `docs/<description>`: Documentation changes (e.g., `docs/team-workflow`, `docs/api-specs`).
  - `refactor/<description>`: Code cleanup without functional changes (e.g., `refactor/models-cleanup`).
  - `chore/<description>`: Dependency or environment updates (e.g., `chore/update-requirements`).
- **Branch Lifecycle**:
  Once a Pull Request (PR) is approved and merged into `main`, the source feature branch **must be deleted** to keep the remote repository clean.

---

## ✍️ 2. Commit Message Conventions

We enforce the **Conventional Commits** specification to make git history readable, traceable, and compatible with automated changelog generation tools.

### Format
```text
<type>: <short description in present tense>

[optional body explaining why this change was made and key implementation details]

[optional footer referencing issue IDs, e.g., Closes #1]
```

### Allowed Types
- **`feat`**: A new feature or capability.
- **`fix`**: A bug fix or correction.
- **`docs`**: Documentation updates only (no source code changes).
- **`refactor`**: Code restructuring without altering external behavior.
- **`test`**: Adding or updating unit tests.
- **`chore`**: Maintenance tasks, dependency updates, or build configuration.

### Examples
- `feat: add data validation function to check incoming CSV schema`
- `fix: correct null percentage calculation in telemetry profiler`
- `docs: document team branching strategy and PR guidelines`
- `chore: update requirements.txt with openai and python-dotenv dependencies`

---

## 🔍 3. Pull Request (PR) & Code Review Process

Pull Requests serve as the mandatory quality gate before any code reaches `main`.

### Workflow Steps
1. Create a feature branch from `main`: `git checkout -b feature/<description>`.
2. Commit changes using conventional commit messages.
3. Push the feature branch to GitHub: `git push origin feature/<description>`.
4. Open a Pull Request from `feature/<description>` targeting `main`.
5. Fill in the standardized PR description, including a summary, list of changes, testing notes, and issue links (`Closes #<issue_number>`).
6. Request review from at least one teammate.
7. **Code Review Checklist**:
   - **Correctness**: Does the logic solve the problem specified in the issue?
   - **Clarity & Readability**: Is the code clean, modular, and self-documenting?
   - **Data Integrity**: Does the change preserve schema expectations and avoid data loss?
   - **Security**: Are API keys and secrets excluded from code and kept in `.env`?
   - **Commit Standards**: Do commit messages follow conventional formatting?
8. Apply feedback and push additional commits to the feature branch.
9. Upon approval, merge the PR into `main` and delete the feature branch.

---

## 📋 4. GitHub Issue Tracking Approach

Every unit of work must begin with an explicit, assignable GitHub Issue before code is written.

- **Action-Oriented Titles**: Titles must start with a verb indicating the action (e.g., `"Ingest customer transaction data into pipeline"` instead of `"Data pipeline"`).
- **Structured Description**: Must outline **Why** this task exists, **What** success looks like, and explicit **Acceptance Criteria**.
- **Labels**: Every issue must have at least one label (`feature`, `bug`, `documentation`, `data-pipeline`, `high-priority`).
- **Assignee**: Exactly one team member is assigned accountability for each open issue.
- **Automated Closing**: Linking a PR to an issue via `Closes #<issue-id>` in the PR description automatically closes the issue when the PR merges.

---

## 🚀 5. Fresh Clone Contributor Guide (Onboarding)

If a new teammate clones this repository for the first time, they must follow these exact steps to contribute a feature without breaking `main`:

```bash
# Step 1: Clone the repository
git clone https://github.com/Abhiram453/Autorag_champs.git
cd Autorag_champs

# Step 2: Set up an isolated virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Step 3: Install dependencies & configure environment
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your local credentials (OPENAI_API_KEY, OPENAI_BASE_URL, CHAT_MODEL)

# Step 4: Pick or create a GitHub Issue
# Identify the issue number (e.g., #12) and assign it to yourself on GitHub

# Step 5: Create a fresh feature branch from latest main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Step 6: Write code and commit with conventional messages
git add .
git commit -m "feat: implement your feature description"

# Step 7: Push branch and open a Pull Request
git push origin feature/your-feature-name
# Go to GitHub (https://github.com/Abhiram453/Autorag_champs/pulls), open PR against main, and add "Closes #12" in the PR description
```
