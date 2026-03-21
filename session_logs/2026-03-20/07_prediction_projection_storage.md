# 2026-03-20 Session Log 07

## Goal

Implement the hybrid prediction-storage phase:

- keep `predictions_{model}` as the canonical write boundary
- add a derived `prediction_songs` table for song-level SQL reads
- validate that canonical rows and the projection stay consistent

## Changes Made

### Prediction projection schema

**New file:** `supabase/migrations/20260323_create_prediction_songs.sql`

- Added `prediction_songs` as a derived per-song projection table
- Added a unique key on `(band, model_version, reference_date, rank)`
- Added read-path indexes for:
  - latest model/band lookups
  - ordered per-reference-date song reads

### Canonical write path

**Modified:** `scripts/generate_predictions.py`

- Canonical prediction writes still upsert one JSON row into
  `predictions_notebook` or `predictions_ckplus`
- Added projection rewrite immediately after the canonical upsert
- Reuses one shared `predicted_at` timestamp for both canonical and projected
  rows

**Modified:** `src/jambandnerd/db/operations.py`

- Added `replace_prediction_projection()` to delete and rewrite projected rows
  for one `(band, model_version, reference_date)` prediction run
- Added `fetch_latest_prediction_songs()` for future consumers that need the
  latest ranked song rows without re-parsing canonical JSON

### Validation and recovery

**Modified:** `scripts/validate_prediction_tables.py`

- Still validates freshness and JSON integrity from canonical prediction tables
- Now also validates `prediction_songs` consistency against the latest
  canonical row by default
- Added `--skip-projection-check` for cases where only canonical freshness is
  needed

**Modified:** `scripts/rebuild_derived_data.py`

- Clearing predictions now also clears `prediction_songs` for the same
  band/model scope

### Docs and admin tooling

**Modified:**

- `docs/reference/specifications/predictions_schema.md`
- `docs/reference/schemas/unified_tables.md`
- `docs/reference/specifications/data_strategy.md`
- `docs/reference/specifications/database.md`
- `docs/reference/models/notebook.md`
- `docs/reference/models/ckplus.md`
- `docs/operations/data_recovery_rebuild.md`
- `scripts/README.md`
- `scripts/admin/get_schemas.py`

These now document the hybrid contract:

- canonical per-run JSON rows
- derived per-song projection rows

### Tests

**Modified:**

- `tests/test_db_operations.py`
- `tests/test_validate_prediction_tables.py`
- `tests/test_operational_recovery_scripts.py`

Coverage added for:

- projection delete-and-rewrite behavior
- latest projected-song reads
- canonical/projection validation mismatch detection
- recovery clearing of `prediction_songs`

## Validation

- `uv run pytest -q tests/test_db_operations.py tests/test_validate_prediction_tables.py tests/test_operational_recovery_scripts.py tests/pipeline/test_run_optimized_pipeline.py`
  passed
- `uv run ruff check scripts/generate_predictions.py scripts/rebuild_derived_data.py scripts/validate_prediction_tables.py scripts/admin/get_schemas.py src/jambandnerd/config/database.py src/jambandnerd/config/__init__.py src/jambandnerd/db/__init__.py src/jambandnerd/db/operations.py tests/test_db_operations.py tests/test_validate_prediction_tables.py tests/test_operational_recovery_scripts.py`
  passed
- `uv run --with mkdocs --with mkdocs-material --with pymdown-extensions mkdocs build --strict`
  passed

## Operational Follow-Up

- Apply `supabase/migrations/20260323_create_prediction_songs.sql` in the live
  database
- Rebuild predictions so `prediction_songs` is populated from canonical rows
- If existing prediction history must be backfilled, run
  `scripts/rebuild_derived_data.py --band all --clear-existing`
