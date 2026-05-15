# Single-Model Production Tables + Show-Day Rollover

## Goal

Prepare the single-model-per-band branch for production by making
`target_show_date` the website-facing prediction anchor, preserving
`reference_date` as model-cutoff metadata, and documenting the Supabase
`setlist_*` contract.

## Changes

- Added a Supabase migration to denormalize live run metadata onto
  `setlist_prediction_songs`: `target_show_date`, `reference_date`,
  `generated_at`, and `top_k`.
- Added site lookup indexes for live prediction rows, retained result rows, and
  projected song rows.
- Updated live prediction projection writes to include the denormalized metadata.
- Updated website prediction selection to prefer the nearest
  `target_show_date >= today` in America/New_York, fall back to the latest
  stale row, and label stale boards as previous-show boards.
- Updated realtime refresh scoping to use `target_show_key` or
  `target_show_date` instead of projection `reference_date`.
- Updated `/last-show` prediction replay reads to prefer `setlist_results` for
  the completed target date and fall back to `setlist_predictions` only when a
  retained result row is missing.
- Updated production contract docs to describe `target_show_date`,
  `reference_date`, and `generated_at` semantics.

## Validation

- `uv run pytest -q tests/test_db_operations.py tests/test_validate_prediction_tables.py`
- `uv run pytest -q tests/test_db_operations.py tests/test_validate_prediction_tables.py tests/test_setlist_schema_contract.py`
- `npm run verify:web`
- `npm run verify:docs`
- `npm run verify:python`
