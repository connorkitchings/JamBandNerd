# Scripts Overview

This directory contains CLI entrypoints for the JamBandNerd pipeline plus a small set of
admin/diagnostic/manual utilities.

## Pipeline entrypoints (stable)

These are the canonical scripts used by docs and GitHub Actions:

- `run_optimized_pipeline.py` — local helper runner for one band or `all`; mirrors the daily workflow sequence, but GitHub Actions YAML is the canonical orchestrator. If collection preflight selects verify-only mode, prediction/backtest work is skipped unless `--force` is passed.
- `generate_live_predictions.py` — generate active live next-show predictions for `--band` using that band's registered model version
- `sync_retained_prediction_corpus.py` — compute and prune the retained last-100 completed-show prediction/metric corpus
- `run_backtest.py` — scoring helper used by the retained corpus sync; supports local raw-table snapshots via `--snapshot-root`
- `verify_data_freshness.py` — CI data-quality check for recent missing setlists
- `generate_pipeline_summary.py` — GitHub Actions monitoring summary for recent completed-show freshness and prediction coverage
- `check_supported_model_freshness.py` — audit supported prediction/accuracy freshness for one band and emit GitHub Actions outputs without failing early
- `validate_prediction_tables.py` — live prediction freshness/JSON integrity check using the latest row by `generated_at`, plus `setlist_prediction_songs` consistency checks
- `validate_accuracy_tables.py` — per-show accuracy freshness/presence check, plus replay-lineage validation for recent scored shows
- `audit_supabase_tables.py` — canonical website-facing Supabase audit that combines live prediction completeness, replay/history coverage, supported-model freshness, and recent raw setlist completeness into one read-only report
- `collection_preflight.py` — classify collection mode and execution mode before the collector starts
- `get_prediction_dates.py` — legacy helper to list available multi-model prediction reference dates
- `get_last_completed_show_date.py` — resolve the most recent completed show date for a band

Band collection scripts (kept at top-level so GitHub Actions and local tooling can address them directly):

- `run_{band}_collection.py` — raw ingestion/upserts for a specific band
- `get_all_bands.py` — returns the repo-authoritative automation band list from `src/jambandnerd/config/bands.py`

Prediction entry points (band-specific wrappers):

- `generate_billy_predictions.py` — Billy Strings wrapper for `generate_predictions.py`
- `generate_billy_ckplus_predictions.py` — Billy Strings CK+ wrapper

## Integrations

- `play_fantasy_goose.py` — auto-play Fantasy Goose using the active Goose prediction board
- `run_live_tracker.py` — poll for live setlist updates during a show

## Recovery and rebuild

- `export_backtest_snapshots.py` — export raw show/setlist tables into local JSON snapshots for offline historical scoring
- `rebuild_prediction_songs.py` — legacy projection rebuild for the old `prediction_songs` table
- `rebuild_derived_data.py` — legacy multi-model rebuild helper for rollback paths
- `backfill_predictions.py` — legacy prediction backfill helper; prefer `sync_retained_prediction_corpus.py` for active website data
- `recover_deal_last50_local.py` — local-first recovery for missing Deal `last_100` historical rows using exported raw snapshots, local scored-run bundles, and per-band Supabase upload/verification
- `wipe_band_data.py` — legacy multi-model destructive cleanup helper

## Diagnostics (stable)

- `diagnose_band_data.py` — diagnose raw table completeness/consistency for a band
- `audit_raw_data.py` — run the raw-data audit across one band or all supported bands
- `audit_shared_model_inputs.py` — audit normalized shared model-input field availability across bands before adding cross-band features
- `check_recent_avg_gap.py` — legacy diagnostic for band/model gap checks
- `compare_models.py` — legacy baseline comparison helper; use it only for offline Phase B evidence against Notebook/Deal-era results
- `evaluate_deal_model.py` — compatibility wrapper that runs the generic comparison workflow for Deal
- `model_readiness.py` — canonical staged readiness workflow for future model promotion: comparison evidence, local snapshot export, historical publish, and backend validation
- `analyze_ablations.py` — rank ablation JSON reports against the canonical Deal baseline and Notebook anchor, then print Batch 2 eligibility and suggested combo experiments

## Admin scripts

Manual tools that write to Supabase. Use with care.

- `admin/add_setlist.py`
- `admin/delete_setlist_data.py`
- `admin/repair_wsp_setlists_range.py`
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

## Local artifact cleanup

The repo ignores generated local artifacts such as `apps/web/.next/`, `.opencode/node_modules/`, `.snapshots/`, `.mypy_cache/`, `output/`, Python bytecode caches, and Playwright test output. These can consume significant disk space but are not part of the tracked repo state.

Safe inspection command:

```bash
git status --short --ignored
```

Safe cleanup command for generated artifacts only:

```bash
find . -name '__pycache__' -type d -prune -exec rm -rf {} + && rm -rf apps/web/.next apps/web/test-results .mypy_cache .pytest_cache .ruff_cache output site
```
