# Fix-Ready Backlog Remediation

## Goal

Address the comprehensive repo review findings around missing-setlist workflow gating, legacy summary reads, verify-only status reporting, and Streamlit-era documentation drift.

## Constraints

- Preserve the selected "degrade and skip" policy for missing recent setlists.
- Do not publish fresh predictions when recent completed-show setlists are incomplete.
- Keep Streamlit material available only as historical context.

## Commands Run

```bash
uv run pytest tests/test_daily_workflow_contract.py -v
uv run pytest tests/test_generate_pipeline_summary.py -v
uv run ruff check src tests scripts
uv run black --check src tests scripts
uv run black tests/test_daily_workflow_contract.py
npm run verify:python
npm run verify:docs
npm run verify:web
gh workflow run daily-pipeline.yml --ref dev -f band=all -f skip_accuracy=false
gh run view 25171483735 --json status,conclusion,createdAt,updatedAt,headBranch,event,displayTitle,jobs
```

## Files Changed

- `.github/workflows/daily-pipeline.yml`
- `scripts/generate_pipeline_summary.py`
- `tests/test_daily_workflow_contract.py`
- `tests/test_generate_pipeline_summary.py`
- `.agent/CONTEXT.md`
- `.agent/PLAYBOOK.md`
- `mkdocs.yaml`
- `session_logs/2026-04-30/01_fix_ready_backlog_remediation.md`

## Validation Status

- Focused workflow tests: 5 passed.
- Focused pipeline summary tests: 9 passed.
- Ruff: passed.
- Black check: passed after formatting `tests/test_daily_workflow_contract.py`.
- `npm run verify:python`: 394 passed, 6 skipped.
- `npm run verify:docs`: passed.
- `npm run verify:web`: not run to completion locally because Node workspace dependencies are not installed; failed at `playwright: command not found`.
- GitHub Actions `Daily Data Pipeline` on `dev`, run `25171483735`: success.
- The Billy matrix job exercised the new missing-setlist path: `Alert on Data Issues` ran, prediction generation, prediction validation, backtest, and accuracy validation were skipped, then freshness/audit/status/summary steps completed successfully.

## Next Step

Open the PR from `dev` to `main` and watch Repo Quality / Website Quality checks.
