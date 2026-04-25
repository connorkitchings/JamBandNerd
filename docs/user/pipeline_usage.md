# Running the Pipeline

This guide provides instructions for running the JamBandNerd data pipelines.

## Recommended Method: Optimized Pipeline

The primary local helper for running the data pipeline is
`run_optimized_pipeline.py`. It mirrors the promoted GitHub Actions daily
workflow for the repo-supported bands, while `.github/workflows/daily-pipeline.yml`
remains the canonical automation contract.

### Usage

- **Run the complete pipeline for all supported bands**:

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
- **Retained Completed-Show Corpus**: `scripts/sync_retained_prediction_corpus.py --band <band> --window 50`
- **Backtesting & Accuracy internals**: `scripts/run_backtest.py --band <band>`

  The backtest script runs in **incremental mode by default**: it checks which shows in the target window are already scored and only computes the new ones. This makes daily reruns near-instant after the initial population.

  - To force a full recompute (e.g. after a data correction or model version bump): add `--no-incremental`
  - To backtest across all historical shows: add `--all-history` (implies full recompute)

> **Branch note (feat/single-model-per-band)**: The `--model` flag has been
> removed from prediction and backtest scripts. Each band has exactly one
> registered model. On `main`/`dev`, the multi-model `--model <model>` flag
> remains available.

- **Legacy baseline comparison** (this branch only): `scripts/compare_to_legacy_baselines.py --band <band>`

Refer to the source code of these scripts for their specific command-line arguments.
