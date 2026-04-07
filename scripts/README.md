# Scripts Overview

This directory contains CLI entrypoints for the JamBandNerd pipeline plus a small set of
admin/diagnostic/manual utilities.

## Pipeline entrypoints (stable)

These are the canonical scripts used by docs and GitHub Actions:

- `run_optimized_pipeline.py` — end-to-end runner for one band or `all`
- `generate_predictions.py` — generate predictions for `--band` and `--model`
- `run_backtest.py` — compute per-show accuracy history and persist historical scored-run lineage
- `save_aggregate_accuracy.py` — compute aggregate accuracy from per-show results
- `verify_data_freshness.py` — CI data-quality check for recent missing setlists
- `generate_pipeline_summary.py` — GitHub Actions monitoring summary for recent completed-show freshness and prediction coverage
- `validate_prediction_tables.py` — prediction freshness/JSON integrity check using the latest row by `predicted_at`, plus `prediction_songs` consistency checks
- `validate_accuracy_tables.py` — per-show and aggregate accuracy freshness/presence check, plus replay-lineage validation for recent scored shows
- `collection_preflight.py` — classify collection mode and execution mode before the collector starts
- `get_prediction_dates.py` — list available prediction reference dates for a band/model
- `get_last_completed_show_date.py` — resolve the most recent completed show date for a band

Band collection scripts (kept at top-level to support dynamic discovery):

- `run_{band}_collection.py` — raw ingestion/upserts for a specific band
- `get_all_bands.py` — discovers supported bands by scanning for `run_*_collection.py`

Prediction entry points (band-specific wrappers):

- `generate_billy_predictions.py` — Billy Strings wrapper for `generate_predictions.py`
- `generate_billy_ckplus_predictions.py` — Billy Strings CK+ wrapper

## Integrations

- `play_fantasy_goose.py` — auto-play Fantasy Goose using notebook predictions
- `run_live_tracker.py` — poll for live setlist updates during a show

## Recovery and rebuild

- `rebuild_prediction_songs.py` — rebuild the `prediction_songs` projection from canonical prediction tables
- `rebuild_derived_data.py` — rebuild predictions, `prediction_songs`, and/or accuracy tables band by band with per-model phase logging and just-in-time clearing
- `backfill_predictions.py` — regenerate historical predictions for one or more band/model combinations
- `wipe_band_data.py` — clear derived outputs per band/model

## Diagnostics (stable)

- `diagnose_band_data.py` — diagnose raw table completeness/consistency for a band
- `audit_raw_data.py` — run the raw-data audit across one band or all supported bands
- `check_recent_avg_gap.py` — check recent average gap for a band/model (requires `--band` and `--model`)
- `evaluate_deal_model.py` — evaluate the Deal model for a band with train/test metrics

## Admin scripts

Manual tools that write to Supabase. Use with care.

- `admin/add_setlist.py`
- `admin/delete_setlist_data.py`
- `admin/get_schemas.py`

## Manual utilities

One-off scripts used for debugging or investigations.

- `manual/test_enhanced_collectors.py`
- `manual/data_quality_check.py`
- `manual/goose/run_goose_transformations.py`
- `manual/wsp/tw_compare_ec_tw.py`
- `manual/wsp/tw_fallback_test.py`
- `manual/validation/test_validation_warnings.py`
- `manual/validation/test_validation_comprehensive.py`

## Shared module

- `common.py` — shared helpers used across pipeline scripts (normalization boundary, Supabase upsert wrappers, band config loading)
