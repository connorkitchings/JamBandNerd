# Projection Refresh Fix

## Goal

Fix the post-merge production recovery gap where Billy and Eggy still failed
`Validate Prediction Tables` after the bounded `prediction_songs` rebuild.

## Constraints

- Keep the fix narrow to the bounded `prediction_songs` rebuild path.
- Do not change validator strictness or the legacy latest-only rebuild behavior.
- Do not run another production recovery attempt until the follow-up PR is merged.

## Root Cause

The bounded rebuild correctly replaced in-window `prediction_songs` rows, but it
reused the historical canonical `predicted_at` from `predictions_*`. The
validator treats `prediction_songs.predicted_at` as projection freshness, so
recent reference dates rebuilt from old canonical rows still looked stale.

## Change

- Updated `scripts/rebuild_prediction_songs.py` so bounded window rebuilds stamp
  a fresh projection `predicted_at` once per band/model rebuild run.
- Kept legacy latest-only rebuild behavior unchanged so ad hoc single-row
  rebuilds still preserve the original canonical timestamp.
- Added tests covering refreshed bounded rebuild timestamps and unchanged legacy
  mode behavior.

## Files Changed Or Artifacts Produced

- `scripts/rebuild_prediction_songs.py`
- `tests/test_operational_recovery_scripts.py`
- `session_logs/2026-04-09/02_projection_refresh_fix.md`
- GitHub PR: `#26` (`codex/projection-refresh-fix` -> `main`)

## Commands Run

- `uv run pytest tests/test_operational_recovery_scripts.py`
- `uv run pytest tests/test_validate_prediction_tables.py`
- `uv run pytest tests/pipeline/test_run_optimized_pipeline.py`
- `uv run ruff check scripts/rebuild_prediction_songs.py tests/test_operational_recovery_scripts.py`

## Validation Status

- Focused recovery-script tests passed.
- Prediction validation tests passed.
- Optimized pipeline orchestration tests passed.
- Focused Ruff check passed.
- Production recovery was not re-run in this session because the fix is waiting on PR `#26`.

## Next Step

Merge PR `#26`, then rerun the bounded projection rebuild and the manual
`daily-pipeline.yml` dispatch for production recovery verification.
