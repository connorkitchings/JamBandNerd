# Fix CI Stale Prediction Validation Failures

## Date
2026-04-07 Session 06

## Summary
Fixed Daily Data Pipeline failures on April 6-7 where um, eggy, and billy bands
failed validation due to stale `prediction_songs` projection rows accumulating
faster than the 30-day cleanup sweep could remove them.

## Root Cause
Mismatch between two systems:
- **Cleanup** (`_cleanup_stale_prediction_songs`): Deleted rows older than **30 days**
- **Validation** (`_check_stale_projection_rows`): Flagged rows with `predicted_at` older than **72 hours**

For bands without recent shows, prediction_songs entries accumulated from daily
runs (reference_dates spanning weeks). These were 9-18 days old — too new for
30-day cleanup, too old for 72h validation. Only the single latest entry was
exempted from the staleness check.

## Changes

### `scripts/validate_prediction_tables.py`
- Added `reference_window_days` parameter (default 7) to `_check_stale_projection_rows`
- Only validates staleness for entries with `reference_date` within ±7 days of today
- Older entries are archival and skip staleness checks

### `src/jambandnerd/db/operations.py`
- Reduced `_cleanup_stale_prediction_songs` `max_age_days` default from 30 → 7
- Aligns cleanup with the validation window so stale entries are actually removed

### `tests/test_validate_prediction_tables.py`
- Replaced `test_validate_predictions_ignores_stale_future_projection_dates` with
  `test_validate_predictions_flags_stale_recent_projection_dates` using dynamic dates
- Added `test_validate_predictions_ignores_stale_old_projection_outside_window` to
  verify old entries outside the window are not flagged

## Verification
- `uv run black src tests scripts` — clean
- `uv run ruff check src tests scripts` — clean
- `uv run pytest` — 196 passed, 6 skipped

## Branch
`fix/ci-stale-prediction-validation` from `dev`

## Constraints
- Do not work on `main`; branch from `dev`
- Every logic change must have tests
- No changes to workflow YAML or entrypoint docs needed

## Commands Run
- `gh run list --limit 15` — identified failed pipeline runs 24100155995 and 24047053702
- `gh run view <id> --log` — extracted per-band validation output
- `uv run black src tests scripts` — formatting clean
- `uv run ruff check src tests scripts` — linting clean
- `uv run pytest` — 196 passed, 6 skipped (6 require SUPABASE_SERVICE_ROLE_KEY)

## Files Changed
- `scripts/validate_prediction_tables.py` — added 7-day reference_date window filter
- `src/jambandnerd/db/operations.py` — reduced cleanup default from 30d to 7d
- `tests/test_validate_prediction_tables.py` — 2 new tests with dynamic dates
- `.agent/PLAYBOOK.md` — added derived-table threshold alignment lesson
- `session_logs/2026-04-07/06_fix_ci_stale_prediction_validation.md` — this log

## Validation Status
All quality gates pass. Not yet committed or pushed.

## Next Step
Commit, push `fix/ci-stale-prediction-validation`, and open a PR to `main`.
