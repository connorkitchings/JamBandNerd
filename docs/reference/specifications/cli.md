# CLI and Scripting Specification

This document defines the command-line interface and scripting design for JamBandNerd. The primary method for interacting with the project's data pipelines is through a series of Python scripts, which are designed to be run with `uv run`.

## Primary Pipeline Script

The main entry point for running the end-to-end pipeline is `scripts/run_optimized_pipeline.py`. This script is the recommended way to run the full data collection, transformation, prediction, and accuracy calculation process.

### Usage

```bash
# Run the complete pipeline for all supported bands
uv run python scripts/run_optimized_pipeline.py --band all

# Run the pipeline for a single band (e.g., Goose)
uv run python scripts/run_optimized_pipeline.py --band goose

# Skip accuracy calculations for a faster run
uv run python scripts/run_optimized_pipeline.py --band all --skip-accuracy
```

## Consolidated Scripts

While the optimized pipeline is recommended for end-to-end runs, the core logic is housed in a few consolidated, parameterized scripts. These can be run individually for granular control or debugging.

### `generate_predictions.py`

Generates and saves predictions for a given band and model.

- `--band <active-band-slug>`: (Required) The band to process. The script accepts any active band returned by the registry/config layer.
- `--model <registered-model-slug>`: (Required) The model to use.
- `--date {YYYY-MM-DD}`: (Optional) The reference date for predictions. Defaults to the next upcoming show.
- `--exclusion-window {N}`: (Optional) For the Notebook model, the number of recent shows to exclude songs from. Defaults to 3.

### `run_backtest.py`

Runs a historical backtest, storing the scored ranked board in
`historical_prediction_runs`, and saving linked per-show accuracy metrics to the
`accuracy_per_show` table. Replay readiness is validated from those linked
`prediction_run_id` rows through `validate_accuracy_tables.py`.

- `--band <active-band-slug>`: (Required) The band to process. The script accepts any active band returned by the registry/config layer.
- `--model <registered-backtest-model-slug>`: (Required) The model to backtest.
- `--shows {N}`: (Optional) Backtest the last N completed shows.
- `--start {YYYY-MM-DD}` / `--end {YYYY-MM-DD}`: (Optional) Define a specific date range for the backtest.
- `--exclusion-window {N}`: (Optional) For the Notebook model, the number of recent shows to exclude songs from. Defaults to 3.

### `save_aggregate_accuracy.py`

Calculates and saves a single aggregate accuracy record based on the results from the backtest.

- `--band <active-band-slug>`: (Required) The band to process. The script accepts any active band returned by the registry/config layer.
- `--model <registered-aggregate-model-slug>`: (Required) The model to aggregate.
- `--shows {N}`: (Optional) The number of recent shows from `accuracy_per_show` to include in the aggregation. Defaults to 100.

### `compare_models.py`

Compares a candidate model against fixed baseline models using the same
historical scoring contract as the backtest flow.

- `--candidate-model <registered-backtest-model-slug>`: (Required) Candidate model to evaluate.
- `--band <slug[,slug...]|all>`: (Optional) Bands to include. Defaults to `all`.
- `--baseline-model <slug>`: (Optional, repeatable) Override baseline models. Defaults to `ckplus` and `notebook`.
- `--window <N>`: (Optional, repeatable) Comparison windows as positive integer show counts. Defaults to `50`.
- `--feature-set-label <label>`: (Optional) Human-readable label for the feature set under test.
- `--fresh-training`: (Optional) Disable persisted artifacts for training-capable candidate models during the comparison run.
- `--include-candidate-diagnostics`: (Optional) Include model-specific diagnostics when the candidate supports them.

### `audit_shared_model_inputs.py`

Audits the normalized show-context fields that could be considered for future
shared model features.

- `--band <slug[,slug...]|all>`: (Optional) Bands to audit. Defaults to `all`.
- `--output <path>`: (Optional) Write the JSON audit report to disk.

### Future Considerations: `jbn` CLI

A `jbn` command-line tool, built with Typer, was originally planned for the project. This tool would provide a more user-friendly interface for running the various pipeline components. While the core logic is implemented in the Python scripts, the `jbn` CLI has been deferred to a future development phase.

## Shared Script Utilities (`common.py`)

Several scripts in the `scripts/` directory rely on shared utility functions housed in `scripts/common.py`. This module provides consistent, reusable logic for common tasks across the pipeline.

### Key Functions

- **`fetch_table(table_name: str)`**: A robust function to fetch all rows from a specified Supabase table. It includes pagination logic to handle large tables, ensuring that the entire dataset is retrieved.

- **`resolve_reference_date(date_str: str | None, shows_df: pd.DataFrame)`**: A crucial utility for determining the date for which predictions should be generated.
  - If a date is provided, it uses that date.
  - If no date is provided, it intelligently finds the date of the next upcoming show in the database.
  - This ensures that running a prediction script without arguments always targets the next relevant show.

- **`prepare_band_data(shows_df: pd.DataFrame, setlists_df: pd.DataFrame)`**: Normalizes the column names and data types of the raw show and setlist DataFrames. This is important because different data sources (e.g., Phish.net vs. elgoose.net) have slightly different schemas. This function creates a consistent data structure before the transformation step.
