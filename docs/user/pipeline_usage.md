# Running the Pipeline

This guide provides instructions for running the JamBandNerd data pipelines.

## Recommended Method: Optimized Pipeline

The primary local helper for running the data pipeline is
`run_optimized_pipeline.py`. It mirrors the promoted GitHub Actions daily
workflow for the daily publishing bands, while `.github/workflows/daily-pipeline.yml`
remains the canonical automation contract.

### Usage

- **Run the complete pipeline for all daily publishing bands**:

    ```bash
    uv run python scripts/run_optimized_pipeline.py --band all
    ```

- **Run the pipeline for a single band** (e.g., Goose):

    ```bash
    uv run python scripts/run_optimized_pipeline.py --band goose
    ```

- **Skip accuracy calculations for a faster run**:

    ```bash
    uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy
    ```

When collection preflight determines a band is idle, the local helper uses a
verify-only path and does not regenerate predictions or backtests. To force a
full local regeneration anyway, pass `--force`.

`--band all` follows `get_daily_pipeline_bands()` from repo config. Eggy remains
collectable through its collection scripts, but is not part of default daily
publishing until it has a promoted website-facing model.

## Website Direction

The public product surface is now the website in `apps/web`, backed by the existing pipeline and Supabase data model.

Primary local website commands:

```bash
npm install
npx playwright install --with-deps chromium
npm run dev:web
npm run verify:web
```

## Advanced Usage: Individual Scripts

For debugging or more granular control, you can run individual pipeline components using the new consolidated scripts.

- **Data Collection**: `run_goose_collection.py`, `run_phish_collection.py`, `run_wsp_collection.py`, `run_eggy_collection.py`, `run_billy_collection.py`, `run_um_collection.py`
- **Live Prediction Generation**: `scripts/generate_live_predictions.py --band <band>`
  - When a recent completed show within the 7-day lookback window is missing setlist data (`< 3` unique songs), prediction generation holds off by default so the existing board in `setlist_predictions` is preserved until the upstream setlist arrives. Pass `--allow-missing-recent-setlists` to override locally.
- **Retained Completed-Show Corpus**: `scripts/sync_retained_prediction_corpus.py --band <band> --window 50`
- **Backtesting & Accuracy internals**: `scripts/run_backtest.py --band <band>`

  The backtest script runs in **incremental mode by default**: it checks which shows in the target window are already scored and only computes the new ones. This makes daily reruns near-instant after the initial population.

  - To force a full recompute (e.g. after a data correction or model version bump): add `--no-incremental`
  - To backtest across all historical shows: add `--all-history` (implies full recompute)

Refer to the source code of these scripts for their specific command-line arguments.


## Live Tracking

Manual live tracking supports Goose and Phish only:

```bash
uv run python scripts/run_live_tracker.py --band goose --date 2026-11-16 --interval 60 --max-iterations 300
```

Each tracker disables response caching, uses 30-second HTTP timeouts, and writes only changed stable setlist content before regenerating predictions. Three consecutive polling, persistence, or regeneration failures exit nonzero. Shrinking snapshots are refused for manual investigation. WSP live tracking is disabled; daily WSP collection still uses Everyday Companion and its completed-show fallback chain.

## Applying Reviewed Corrections

Scheduled correction sweeps remain dry-run. Review detected changes before manually dispatching `Weekly Correction Sweep` with `dry_run=false`, or running the existing CLI:

```bash
uv run python scripts/run_correction_sweep.py --band goose --dry-run
uv run python scripts/run_correction_sweep.py --band goose --no-dry-run
```

For active model bands, a successful raw apply forces a rebuild of the retained last-50 completed-show corpus (`incremental=False`), generates the live board if a future target exists, and validates prediction tables and exact retained accuracy/replay coverage. It does not require an all-history backtest. Zero-applies, dry-runs, and inactive model bands skip derived refresh.

Inspect `post_correction_refresh` in the JSON report. If derived refresh fails after raw writes, the command exits nonzero and reports the failed stage and recovery commands; raw writes remain applied. After successful CLI refresh, invalidate the website band cache as described in [Website Delivery](../operations/website_delivery.md#cache-revalidation). The manual workflow performs that cache request after successful refresh and preserves reports on failure.

The daily workflow refreshes its future-show target after collection and records final band status only after validation, audits, freshness enforcement, and cache delivery. Collection success alone does not authorize automated Fantasy Goose submission.
