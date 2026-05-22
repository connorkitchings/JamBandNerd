# Complete Single-Model-Per-Band Transition

## Goal

Remove all legacy multi-model (`model_slug`) architecture from the codebase, completing the transition to the single-model-per-band design codified in ADR 0001.

## Changes

### Backend Registry & Config
- Rewrote `src/jambandnerd/models/registry.py` to export only band-keyed functions: `list_active_bands()`, `get_band_metadata()`, `get_band_model_version()`, `build_band_predictor()`, `get_band_serializer()`. Removed all model-slug-keyed functions (`build_predictor`, `get_model_definition`, `list_model_slugs`, etc.) and `ModelDefinition` dataclass.
- Simplified `src/jambandnerd/models/metadata.py` to only `BandMetadata` and `BAND_METADATA`. Removed `ModelMetadata`, `MODEL_METADATA`, `ModelLifecycleStage`, `ModelWebVisibility`.
- Cleaned `src/jambandnerd/config/models.py`: removed `MODEL_VERSIONS`, `ENABLED_MODELS`. Kept `ACTIVE_BANDS` and Deal hyperparameters (still used by shared `DealPredictor` base class).
- Cleaned `src/jambandnerd/config/database.py`: removed `PREDICTION_TABLES`, `PREDICTION_SONGS_TABLE`, `HISTORICAL_PREDICTION_RUNS_TABLE`, `NEXT_SHOW_*`, `COMPLETED_SHOW_*` constants. Kept only `SETLIST_*` and `RAW_TABLE_SUFFIX`.
- Cleaned `src/jambandnerd/config/__init__.py` to match.

### Legacy Model Classes
- Moved `src/jambandnerd/models/ckplus/` to `src/jambandnerd/models/legacy/ckplus/`.
- Moved `src/jambandnerd/models/comparison.py` to `src/jambandnerd/models/legacy/comparison.py`.
- Kept `deal/` and `notebook/` in place (shared infrastructure used by per-band models).
- Rewrote `src/jambandnerd/models/readiness.py` to only keep `is_band_promotion_eligible` (band-keyed). Removed legacy `build_model_readiness_report`.
- Removed `src/jambandnerd/models/serialization.py` (thin legacy wrapper).
- Removed `src/jambandnerd/models/model_test_cache.py`.
- Updated `src/jambandnerd/models/__init__.py` to remove legacy model references.

### DB Operations
- Removed 11 legacy functions from `src/jambandnerd/db/operations.py`: `replace_prediction_projection`, `upsert_next_show_prediction_run`, `replace_next_show_prediction_projection`, `upsert_completed_show_prediction_run`, `prune_completed_show_corpus`, `upsert_historical_prediction_run`, `fetch_historical_prediction_run`, `fetch_latest_prediction_songs`, `fetch_prediction_songs_for_date`, `check_prediction_staleness`, `fetch_scored_show_ids`. Also removed `_cleanup_stale_prediction_songs` helper.
- Updated `src/jambandnerd/db/__init__.py` to match.

### Scripts
- Removed: `generate_predictions.py`, `backfill_predictions.py`, `rebuild_prediction_songs.py`, `get_prediction_dates.py`, `rebuild_derived_data.py`, `analyze_ablations.py`, `recover_deal_last50_local.py`, `wipe_band_data.py`, `model_readiness.py`.
- Moved to `scripts/legacy/`: `compare_models.py`, `evaluate_deal_model.py`.
- Rewrote `scripts/run_backtest.py`: removed `--model` flag, `legacy_lineage` path, `local_cache` support, `model_slug` in records. Band-only now.
- Updated `scripts/run_live_tracker.py`: uses `generate_live_predictions()` instead of legacy `generate_predictions()`.
- Updated `scripts/generate_pipeline_summary.py`: queries `setlist_predictions` instead of `predictions` table.
- Updated `scripts/run_optimized_pipeline.py`: removed `model=None` from `run_backtest` call.

### Tests
- Removed: `test_compare_models.py`, `test_generate_predictions.py`, `test_backfill_predictions.py`, `test_recover_deal_last50_local.py`, `test_model_readiness.py` (pipeline), `test_model_readiness.py` (models), `test_model_test_cache.py`, `test_analyze_ablations.py`, `test_operational_recovery_scripts.py`, `test_model_registry.py`, `test_ckplus_model.py`, `test_evaluate_deal_model.py`.
- Updated: `test_run_backtest.py`, `test_db_operations.py`, `test_prediction_reference_date_semantics.py`, `live_helpers.py`, `test_generate_pipeline_summary.py`.

### Docs
- Updated ADR 0001 status to reflect Phase A + Phase B completion.
- Updated `scripts/README.md` to reflect new script layout.

## Verification

```bash
uv run pytest tests/ -x -q                    # 568 passed, 6 skipped
uv run ruff check src/ scripts/ tests/         # 0 errors
npm run verify:web                             # 10 passed
npm run verify:docs                            # OK
```

## Key Constraints Preserved

- Deal hyperparameters kept in config (used by shared `DealPredictor` base class)
- `models/deal/` and `models/notebook/` kept in place (shared infrastructure)
- Legacy scripts archived in `scripts/legacy/` (not deleted)
- Legacy comparison module archived in `models/legacy/`
- Eggy remains collection-only (deferred)
