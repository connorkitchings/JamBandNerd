# Single Model Backend Phase A

## Goal

Continued `feat/single-model-per-band` after integrating current `main`.
The slice keeps the website cutover deferred and routes backend Phase A writes,
validators, and workflow orchestration through the additive `setlist_*` tables.

## Constraints

- Preserve current `main` CI/dependency fixes and Fantasy Goose artifact-version
  correction.
- Keep legacy prediction helpers and legacy tables available for rollback and
  comparison.
- Do not cut over `apps/web` in this backend-only slice.
- Keep Eggy out of the first active single-model band set.
- Skip Supabase dry-runs when local Supabase environment variables are absent.

## Commands Run

- `git merge --no-ff main`
- `git restore --source main -- apps/web/src/components/data-state.tsx apps/web/src/components/live-tracker.tsx apps/web/src/lib/data/accuracy.ts apps/web/src/lib/data/parsers.ts apps/web/src/lib/data/predictions.ts apps/web/src/lib/data/replay.ts`
- `uv run python -m py_compile scripts/audit_supabase_tables.py scripts/check_supported_model_freshness.py scripts/check_prediction_storage_rollout.py scripts/validate_accuracy_tables.py scripts/validate_prediction_tables.py scripts/run_optimized_pipeline.py scripts/run_backtest.py scripts/generate_live_predictions.py scripts/sync_retained_prediction_corpus.py`
- `uv run black ...`
- `uv run ruff check src scripts tests --fix`
- `uv run ruff check src scripts tests`
- `uv run pytest tests/test_db_operations.py tests/models/test_model_registry.py tests/pipeline/test_generate_live_predictions.py tests/pipeline/test_sync_retained_prediction_corpus.py tests/pipeline/test_run_backtest.py tests/test_validate_prediction_tables.py tests/test_validate_accuracy_tables.py tests/test_check_prediction_storage_rollout.py -q`
- `npm run verify:python`
- `npm run verify:docs`
- `npm run verify:web`

## Files Changed Or Artifacts Produced

- Added canonical `SETLIST_*` table constants and exports.
- Added setlist storage helpers in `src/jambandnerd/db/operations.py` for live
  prediction runs, projection replacement, retained results, accuracy rows,
  corpus pruning, and already-scored target lookup.
- Updated Phase A CLIs to use band-keyed registry APIs and remove the active
  `--model` dimension:
  - `scripts/generate_live_predictions.py`
  - `scripts/sync_retained_prediction_corpus.py`
  - validators, freshness checks, Supabase audit, rollout checker, and local
    optimized pipeline.
- Updated retained scoring to persist `p10`, `p25`, `p50`, recall fields, and
  `weighted_precision_score = 0.2*p10 + 0.7*p25 + 0.1*p50`.
- Updated daily/backfill workflow orchestration for the active single-model band
  set, with Eggy excluded from the first rollout.
- Restored `apps/web` data reads to the current main behavior for this slice.
- Removed the obsolete split-table migration in favor of the existing
  `20260425_create_setlist_tables.sql` migration.
- Updated active docs and tests for the Phase A `setlist_*` contract.
- Produced this session log.

## Validation

- `uv run pytest tests/test_db_operations.py tests/models/test_model_registry.py tests/pipeline/test_generate_live_predictions.py tests/pipeline/test_sync_retained_prediction_corpus.py tests/pipeline/test_run_backtest.py tests/test_validate_prediction_tables.py tests/test_validate_accuracy_tables.py tests/test_check_prediction_storage_rollout.py -q`
  - 43 passed
- `npm run verify:python`
  - 341 passed, 6 skipped
- `npm run verify:docs`
  - MkDocs strict build passed
- `npm run verify:web`
  - Next build passed
  - Playwright smoke: 11 passed, 11 skipped

Supabase dry-runs were not executed because `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY` were not present in the local environment.

## Next Step

Run the Goose Supabase dry-runs once `SUPABASE_URL` and
`SUPABASE_SERVICE_ROLE_KEY` are available locally.
