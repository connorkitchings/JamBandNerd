# Workflow Stability Hardening

## Goal
- Diagnose and stabilize production daily and weekly GitHub Actions failures before continuing manual site review.

## Constraints
- Do not push to `main`.
- Preserve existing local changes in the dirty `dev` worktree.
- Keep the daily production pipeline behavior intact after the manual rerun passed.

## Commands Run
- `gh run list --workflow daily-pipeline.yml --limit 10`
- `gh run list --workflow weekly-correction-sweep.yml --limit 10`
- `gh run view 26185797482 --log`
- `gh run view 26120454361 --log`
- `gh run view 26120745544 --log`
- `gh run view 26117836836 --log`
- `gh run view 26194215363 --json jobs,conclusion,status,url`
- `uv run pytest -q tests/test_daily_workflow_contract.py tests/pipeline/test_run_backtest.py`
- `uv run ruff check scripts/run_backtest.py tests/test_daily_workflow_contract.py tests/pipeline/test_run_backtest.py`
- `gh run list --limit 5`

## Files Changed Or Artifacts Produced
- `.github/workflows/daily-pipeline.yml`
  - Added `--require-output` to live prediction generation.
- `.github/workflows/weekly-correction-sweep.yml`
  - Disabled cron schedules while preserving manual dispatch.
- `apps/web/src/lib/data/predictions.ts`
  - Scoped date-based prediction/history lookups to the latest active model version when available.
- `docs/operations/github_actions.md`
  - Documented the weekly correction sweep as manual-only while the detector is missing.
- `scripts/run_backtest.py`
  - Trimmed Supabase write-key values before prefix validation.
- `tests/test_daily_workflow_contract.py`
  - Enforced `--require-output` and added a weekly schedule guard when `correction_detector.py` is missing.
- `tests/pipeline/test_run_backtest.py`
  - Added Supabase write-key preflight coverage for whitespace and publishable-key rejection.
- `.agent/PLAYBOOK.md`
  - Added durable workflow/secret hardening lessons.
- `session_logs/2026-05-19/02_supabase_site_workflow_review.md`
  - Captured prior production Supabase/site workflow review notes.

## Validation Status
- Focused tests passed: `14 passed`.
- Ruff passed on touched Python files.
- Latest GitHub Actions status after secret repair:
  - Daily Data Pipeline `26194215363`: success.
  - Fantasy Goose `26194393444`: success.
  - Hosted Website Smoke `26193961451`: success.

## Next Step
- Repair or replace `scripts/run_correction_sweep.py` before re-enabling the weekly cron schedule.
