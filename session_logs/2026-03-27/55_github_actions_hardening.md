# Session Log: 2026-03-27 (GitHub Actions Hardening)

## Goal

Ensure the repository's GitHub Actions workflows are aligned with the current repo setup and reduce workflow-only failures caused by inconsistent environment bootstrapping.

## Constraints

- Follow `.agent/AGENTS.md` boot order and use the `start-session` skill first.
- Do not work on `main`.
- Keep workflow commands aligned with documented repo tooling (`uv`, `npm`, canonical scripts).
- Validate locally where possible without relying on GitHub-hosted secrets.

## Commands Run

```bash
git checkout -b codex/github-actions-hardening
git status --short
rg --files .github/workflows
uv run pytest tests/test_validate_prediction_tables.py tests/test_validate_accuracy_tables.py tests/test_generate_pipeline_summary.py
uv run ruff check src tests scripts
npm run lint:web
npm run build:web
ruby -e 'require "yaml"; Dir[".github/workflows/*.yml"].each { |f| YAML.load_file(f) }; puts "yaml ok"'
git diff --check
```

## Files And Artifacts

- `.github/workflows/daily-pipeline.yml` - switched to lockfile-backed `uv` setup, simplified matrix selection for manual runs, and removed skip-only fanout behavior.
- `.github/workflows/backfill-predictions.yml` - switched to lockfile-backed `uv` setup and `uv run` script execution.
- `.github/workflows/dependency-audit.yml` - replaced ad hoc `uv` install with `astral-sh/setup-uv`.
- `.github/workflows/live-tracker.yml` - updated action versions, added explicit secret validation, and aligned execution with `uv run`.
- `.github/workflows/repo-quality.yml` - now installs through `uv sync --locked --extra dev`.
- `.github/workflows/test_secrets.yml` - treats Supabase secrets as required and `PHISH_API_KEY` as warning-only unless a Phish-specific workflow is run.
- `docs/operations/github_actions.md` - documented lockfile-backed `uv` setup and targeted manual matrix behavior.

## Validation

- YAML parse: passed for all `.github/workflows/*.yml`
- `git diff --check`: passed
- `uv run pytest tests/test_validate_prediction_tables.py tests/test_validate_accuracy_tables.py tests/test_generate_pipeline_summary.py`: 15 passed
- `uv run ruff check src tests scripts`: passed
- `npm run lint:web`: passed
- `npm run build:web`: passed after rerunning outside the local sandbox because Next/Turbopack needed permissions that the sandbox blocked

## Next Step

- Run the updated workflows in GitHub with real secrets to validate the secret-gated paths (`daily-pipeline`, `backfill-predictions`, `live-tracker`) end to end.
