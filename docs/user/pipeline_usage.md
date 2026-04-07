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
npm run dev:web
npm run build:web
```

The legacy Streamlit app remains available only for internal legacy/debugging use. Its run instructions live in `docs/operations/streamlit_deploy.md`, not in the main pipeline workflow.

## Advanced Usage: Individual Scripts

For debugging or more granular control, you can run individual pipeline components using the new consolidated scripts.

- **Data Collection**: `run_goose_collection.py`, `run_phish_collection.py`, `run_wsp_collection.py`, `run_eggy_collection.py`, `run_billy_collection.py`, `run_um_collection.py`
- **Prediction Generation**: `scripts/generate_predictions.py --band <band> --model <model>`
- **Backtesting & Accuracy**: `scripts/run_backtest.py --band <band> --model <model>`, `scripts/save_aggregate_accuracy.py --band <band> --model <model>`

Refer to the source code of these scripts for their specific command-line arguments.
