# 2026-03-21 Session Log 01

## Goal

Wrap the multi-step data-strategy session by finalizing the repo state after:

- documentation of the show-centric data contract
- normalization and `accuracy_per_show.show_id` alignment
- recovery tooling for audit/rebuild workflows
- hybrid prediction storage with `prediction_songs`
- live Supabase rebuild and validation

## Constraints

- Preserve the canonical run-level prediction tables as the source of truth
- Do not lose the session's accumulated doc, migration, and test changes while
  wrapping up
- Keep the database-facing recovery path rebuildable rather than repair-based

## Commands Run

- `uv run pytest -q tests/test_db_operations.py tests/test_validate_prediction_tables.py tests/test_operational_recovery_scripts.py tests/pipeline/test_run_optimized_pipeline.py`
- `uv run ruff check scripts/generate_predictions.py scripts/rebuild_derived_data.py scripts/validate_prediction_tables.py scripts/admin/get_schemas.py src/jambandnerd/config/database.py src/jambandnerd/config/__init__.py src/jambandnerd/db/__init__.py src/jambandnerd/db/operations.py tests/test_db_operations.py tests/test_validate_prediction_tables.py tests/test_operational_recovery_scripts.py`
- `uv run --with mkdocs --with mkdocs-material --with pymdown-extensions mkdocs build --strict`
- `uv run python -u scripts/rebuild_derived_data.py --band all --clear-existing`
- `uv run python scripts/validate_prediction_tables.py`

## Files Changed Or Artifacts Produced

- Canonical strategy and schema docs updated under `docs/reference/`
- New operational runbook: `docs/operations/data_recovery_rebuild.md`
- New scripts:
  - `scripts/audit_raw_data.py`
  - `scripts/rebuild_derived_data.py`
- Shared normalization and projection logic updated in:
  - `src/jambandnerd/transformations/normalization.py`
  - `src/jambandnerd/db/operations.py`
  - `scripts/generate_predictions.py`
  - `scripts/validate_prediction_tables.py`
- New migrations:
  - `supabase/migrations/20260322_accuracy_per_show_show_id_text.sql`
  - `supabase/migrations/20260323_create_prediction_songs.sql`
- Session artifacts:
  - `session_logs/2026-03-20/04_data_strategy_docs.md`
  - `session_logs/2026-03-20/05_normalization_and_accuracy_show_id.md`
  - `session_logs/2026-03-20/06_operational_recovery_tooling.md`
  - `session_logs/2026-03-20/07_prediction_projection_storage.md`

## Validation Status

- Repo-local tests, lint, and docs build passed
- Live Supabase migration for `prediction_songs` was applied
- Full all-band rebuild completed successfully
- Final prediction validation passed for Notebook and CK+ across:
  - Goose
  - Eggy
  - Phish
  - WSP
  - Billy
  - UM

## Next Step

Monitor the next scheduled production pipeline run and confirm `prediction_songs`
continues to match the latest canonical prediction rows without manual rebuilds.
