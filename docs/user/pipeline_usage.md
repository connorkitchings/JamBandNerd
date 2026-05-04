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

## Incremental Collection (Daily Workflow)

The data collection scripts now support incremental collection modes to improve efficiency:

### Band-Specific Incremental Features

| Band | Incremental Method | Description |
|------|-------------------|-------------|
| **Eggy** | `updated_at` timestamp | Only collects records modified since last successful collection |
| **UM** | `api_updated_at` timestamp | Only collects records modified since last successful collection |
| **Goose** | Show count comparison | Skips collection if upstream show count matches database |
| **Billy** | Show count comparison | Skips collection if upstream show count matches database (60-day window) |
| **Phish** | Year-window + incremental setlists | Only fetches setlists for shows without existing data |
| **WSP** | 90-day rolling window | Year-based collection with incremental setlist skipping |

### Controlling Incremental Mode

For **Eggy** and **UM**:
```bash
# Run with incremental collection (default)
uv run python scripts/run_eggy_collection.py

# Force full refresh (disable incremental)
uv run python scripts/run_eggy_collection.py --no-incremental
```

For **Goose** and **Billy**:
```bash
# Skip if show count unchanged (default)
uv run python scripts/run_goose_collection.py
uv run python scripts/run_billy_collection.py

# Force collection regardless of count
uv run python scripts/run_goose_collection.py --force
uv run python scripts/run_billy_collection.py --force
```

## Weekly Correction Sweep (Tuesdays)

Every Tuesday, a correction sweep runs to detect and apply fixes to existing data. This catches upstream corrections that incremental collection might miss.

### Schedule

| Time (ET) | Band |
|-----------|------|
| 10:00 AM | Goose |
| 11:00 AM | Phish |
| 12:00 PM | Eggy |
| 1:00 PM | Billy Strings |
| 2:00 PM | Widespread Panic |
| 3:00 PM | Umphrey's McGee |

### Manual Trigger

You can run a correction sweep manually:

```bash
# Dry run (detect only, don't apply)
uv run python scripts/run_correction_sweep.py --band goose --dry-run

# Apply corrections
uv run python scripts/run_correction_sweep.py --band goose --no-dry-run

# Custom window (default: 730 days)
uv run python scripts/run_correction_sweep.py --band goose --window-days 365
```

## Advanced Usage: Individual Scripts

For debugging or more granular control, you can run individual pipeline components using the new consolidated scripts.

- **Data Collection**: `run_goose_collection.py`, `run_phish_collection.py`, `run_wsp_collection.py`, `run_eggy_collection.py`, `run_billy_collection.py`, `run_um_collection.py`
- **Live Prediction Generation**: `scripts/generate_live_predictions.py --band <band> --model <model>`
- **Retained Completed-Show Corpus**: `scripts/sync_retained_prediction_corpus.py --band <band> --window 50`
- **Backtesting & Accuracy internals**: `scripts/run_backtest.py --band <band> --model <model>`
- **Correction Sweep**: `scripts/run_correction_sweep.py --band <band>`

  The backtest script runs in **incremental mode by default**: it checks which shows in the target window are already scored and only computes the new ones. This makes daily reruns near-instant after the initial population.

  - To force a full recompute (e.g. after a data correction or model version bump): add `--no-incremental`
  - To backtest across all historical shows: add `--all-history` (implies full recompute)

Refer to the source code of these scripts for their specific command-line arguments.
