# Git

## Branches

| Role | Branch |
|------|--------|
| PM | `main` / `pm` |
| Database | `db` |
| Backend | `backend` |
| Frontend | `frontend` |
| Data Science | `ds` |
| Orchestration | `orch` / `orchestration` |

## Workflow

1. Work on your branch.
2. Push changes to GitHub.
3. Open a pull request to `main`.
4. Review, merge, and clean up branches after verification.

## Useful commands

```bash
git fetch
git status
git pull --ff-only
git checkout <branch>
git add .
git commit -m "short message"
git push origin <branch>
```

## Current repo usage

- `main` is the integration branch.
- GitHub Pages deploys documentation from CI after a successful MkDocs build.
