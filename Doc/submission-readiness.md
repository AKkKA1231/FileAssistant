# Submission Readiness

## Repository Deliverables

| Deliverable | Status | Location or action |
|---|---|---|
| Source code | Ready | `src/` |
| Dependency list | Ready | `requirements.txt` and `pyproject.toml` |
| Fictional sample data | Ready | `data/resumes/` (seventeen files) |
| Setup and usage guide | Ready | `README.md` |
| Tool contracts | Ready | `Doc/tool-contracts.md` |
| Architecture and plans | Ready | `Doc/` |
| Automated tests | Ready | `tests/` |
| Two-to-three-minute video | Pending external action | Record with `Doc/demo-guide.md` |
| GitHub repository URL | Pending external action | Create/push the repository, then copy its URL |

## Final Local Checks

Run these commands from the repository root:

```powershell
python -m pytest
python -m pytest --cov=src --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m pip check
git check-ignore -v .env
git status --short
```

The ignore check must identify `.env`. Review `git status` before committing and
ensure the local `.env`, generated summaries, caches, and virtual environment are
not staged.

## Secret Safety

Before the first push, search the files intended for commit for common credential
patterns. Do not print matching secret values into screenshots or shared logs.
If a real key has ever appeared in a chat, commit, recording, or other shared
location, revoke it in the provider dashboard and create a replacement.

## Suggested Git Workflow

```powershell
git add .
git status --short
git commit -m "feat: implement Groq-powered file system assistant"
git branch -M main
git remote add origin <your-github-repository-url>
git push -u origin main
```

Inspect the staged file list before committing. Creating a GitHub repository,
pushing code, publishing a video, and submitting their URLs require the owner's
accounts and are intentionally not automated by this project.

## Final Submission Checklist

- All automated tests and quality checks pass.
- The GitHub repository is accessible to the evaluator.
- The repository contains no real API keys or personal resume data.
- The README commands work in a clean environment.
- The demo video shows live list, search, read, and write operations.
- The video lasts two to three minutes and its link is accessible.
- The submitted GitHub and video URLs point to the final versions.
