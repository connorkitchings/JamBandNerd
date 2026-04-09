# Projection Refresh Fix

## Goal

Fix the post-merge production recovery gap where Billy and Eggy still failed
`Validate Prediction Tables` after the bounded `prediction_songs` rebuild.

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

## Commands Run

- `uv run pytest tests/test_operational_recovery_scripts.py`
- `uv run pytest tests/test_validate_prediction_tables.py`
- `uv run pytest tests/pipeline/test_run_optimized_pipeline.py`
- `uv run ruff check scripts/rebuild_prediction_songs.py tests/test_operational_recovery_scripts.py`

## Next Step

Push the fix branch, open a PR to `main`, merge it, then rerun the bounded
projection rebuild and the manual `daily-pipeline.yml` dispatch for production
recovery verification.
