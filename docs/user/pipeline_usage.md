# Running the Pipeline

This guide provides instructions for running the JamBandNerd data pipelines.

## Recommended Method: Optimized Pipeline

The primary and recommended way to run the data pipeline is with the `run_optimized_pipeline.py` script. This script efficiently handles data collection, transformations, predictions, and accuracy calculations for the specified band(s).

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
- **Prediction Generation**: `scripts/generate_predictions.py --band <band> --model <model>`
- **Backtesting & Accuracy**: `scripts/run_backtest.py --band <band> --model <model>`

  The backtest script runs in **incremental mode by default**: it checks which shows in the target window are already scored and only computes the new ones. This makes daily reruns near-instant after the initial population.

  - To force a full recompute (e.g. after a data correction or model version bump): add `--no-incremental`
  - To backtest across all historical shows: add `--all-history` (implies full recompute)

Refer to the source code of these scripts for their specific command-line arguments.
