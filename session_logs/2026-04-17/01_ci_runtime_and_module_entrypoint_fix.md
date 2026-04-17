# Session Log - 2026-04-17 / 01

## Goal

- Repair the GitHub Actions failures from the April 15-16 daily pipeline runs by fixing the Playwright runtime dependency boundary and the CI module invocation path for the Supabase audit scripts.

## Constraints

- Leave the existing unrelated dirty worktree changes intact.
- Preserve the current daily-pipeline failure policy rather than masking errors.
- Keep verification focused on the CI-facing entrypoints touched by the fix.

## Commands Run

```bash
gh auth status
gh run list --limit 20 --json databaseId,displayTitle,event,headBranch,headSha,name,status,conclusion,createdAt,updatedAt,url
gh run view 24529758059 --json name,displayTitle,event,status,conclusion,url,jobs
gh run view 24474096964 --json name,displayTitle,event,status,conclusion,url,jobs
gh run view 24529758059 --job 71709594860 --log | rg -n -C 6 'Install Playwright Browsers|playwright|##\\[error\\]|Error:'
gh run view 24529758059 --job 71709594867 --log | rg -n -C 6 'Audit Website Supabase Tables|workflow-audits|No files were found|##\\[error\\]|Traceback|ERROR|error:'
uv lock
uv sync --locked --no-dev
uv run python -m scripts.audit_supabase_tables --help
uv run python -m scripts.check_supported_model_freshness --help
uv run python -m playwright --help
uv sync --locked --extra dev
npm run verify:python
uv run pytest -q tests/test_audit_supabase_tables.py tests/test_check_supported_model_freshness.py tests/test_browser.py tests/test_fantasy_goose.py
```

## Files And Artifacts

- `pyproject.toml`
- `uv.lock`
- `.github/workflows/daily-pipeline.yml`
- `.github/workflows/fantasy-goose.yml`
- `scripts/__init__.py`
- `docs/operations/github_actions.md`

## Validation

- Confirmed the failing workflow root causes from GitHub Actions logs:
  - `wsp` / `eggy`: `Failed to spawn: playwright`
  - audit step: `ModuleNotFoundError: No module named 'scripts'`
- Confirmed the repaired module entrypoints locally:
  - `uv run python -m scripts.audit_supabase_tables --help`
  - `uv run python -m scripts.check_supported_model_freshness --help`
- Confirmed Playwright CLI availability from the non-dev runtime environment:
  - `uv sync --locked --no-dev`
  - `uv run python -m playwright --help`
- Focused regression slice passed:
  - `tests/test_audit_supabase_tables.py`
  - `tests/test_check_supported_model_freshness.py`
  - `tests/test_browser.py`
  - `tests/test_fantasy_goose.py`
- `npm run verify:python` still fails due unrelated pre-existing dirty-worktree failures in `tests/pipeline/test_backfill_predictions.py` against `scripts/backfill_predictions.py`, not due this CI fix.

## Next Step

- Push the CI repair separately from the in-progress WSP parser work, then rerun the daily pipeline or targeted workflows (`Daily Data Pipeline`, `Fantasy Goose`) to confirm the GitHub-hosted runners now reach browser install and Supabase audit successfully.
