# Session Log: 2026-03-25 - Historical Prediction Lineage Hardening

## Goal

Add a canonical historical scored-run store so `accuracy_per_show` rows can be
traced back to the exact ranked board produced by `run_backtest.py`.

## Constraints

- Keep the live prediction storage contract unchanged
- Do not overload `prediction_songs` or `predictions_{model}` with historical
  backtest snapshots
- Work in the existing dirty web/UI worktree without reverting unrelated files

## Commands run

- `uv run black scripts/run_backtest.py scripts/generate_predictions.py scripts/rebuild_derived_data.py src/jambandnerd/db/operations.py src/jambandnerd/config/database.py src/jambandnerd/config/__init__.py src/jambandnerd/db/__init__.py src/jambandnerd/models/serialization.py tests/pipeline/test_run_backtest.py tests/test_db_operations.py tests/test_operational_recovery_scripts.py`
- `uv run ruff check --fix scripts/generate_predictions.py scripts/run_backtest.py src/jambandnerd/db/__init__.py`
- `uv run ruff check scripts/run_backtest.py scripts/generate_predictions.py scripts/rebuild_derived_data.py src/jambandnerd/db/operations.py src/jambandnerd/config/database.py src/jambandnerd/config/__init__.py src/jambandnerd/db/__init__.py src/jambandnerd/models/serialization.py tests/pipeline/test_run_backtest.py tests/test_db_operations.py tests/test_operational_recovery_scripts.py`
- `uv run pytest tests/pipeline/test_run_backtest.py tests/test_db_operations.py tests/test_operational_recovery_scripts.py`

## Files changed

- `scripts/generate_predictions.py`
- `scripts/rebuild_derived_data.py`
- `scripts/run_backtest.py`
- `src/jambandnerd/config/__init__.py`
- `src/jambandnerd/config/database.py`
- `src/jambandnerd/db/__init__.py`
- `src/jambandnerd/db/operations.py`
- `src/jambandnerd/models/serialization.py`
- `supabase/migrations/20260325_create_historical_prediction_runs.sql`
- `tests/pipeline/test_run_backtest.py`
- `tests/test_db_operations.py`
- `tests/test_operational_recovery_scripts.py`
- `docs/reference/specifications/predictions_schema.md`
- `docs/reference/specifications/data_strategy.md`
- `docs/reference/schemas/unified_tables.md`
- `docs/reference/specifications/cli.md`
- `docs/operations/data_recovery_rebuild.md`
- `scripts/README.md`

## Validation status

- Formatting: passed
- Ruff: passed
- Targeted tests: 13 passed

## Notes

- `run_backtest.py` now persists a canonical row in
  `historical_prediction_runs` before writing the linked `accuracy_per_show`
  row.
- The stored historical payload reuses the same model-specific JSON shape as the
  live prediction write path.
- `rebuild_derived_data.py --clear-existing` now clears historical run rows for
  the selected band/model accuracy scope.

## Next step

Apply `supabase/migrations/20260325_create_historical_prediction_runs.sql` and
run a recent backfill window so new `accuracy_per_show` rows get
`prediction_run_id` coverage in Supabase.
