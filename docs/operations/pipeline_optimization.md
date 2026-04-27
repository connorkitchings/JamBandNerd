# Pipeline Optimization Guide

This guide covers the performance and maintainability optimizations implemented for the JamBandNerd data pipeline.

## Overview

The JamBandNerd pipeline has been refactored to improve maintainability, reduce complexity, and maintain efficient execution. The core of this optimization is **script consolidation**.

Previously, the pipeline relied on numerous individual scripts for each band and model combination. This has been replaced by a small set of powerful, parameterized scripts that handle all core logic. This change significantly simplifies the project structure and the automation workflows.

## Consolidated Scripts

The primary optimization is the consolidation of 14+ scripts into a few core orchestrators and runners. This follows the **Don't Repeat Yourself (DRY)** principle, making the codebase easier to manage and extend.

- `scripts/run_optimized_pipeline.py`: The main entry point for running the end-to-end pipeline locally. It orchestrates calls to the other consolidated scripts.
- `scripts/generate_live_predictions.py`: A single script to generate the active next-show prediction board for any active band.
- `scripts/sync_retained_prediction_corpus.py`: A corpus sync wrapper that scores each band's registered model version against the retained last-100 eligible completed shows and prunes older derived rows.
- `scripts/run_backtest.py`: The lower-level backtest/scoring engine used by the retained corpus sync.

## GitHub Actions Optimization

The GitHub Actions workflow (`.github/workflows/daily-pipeline.yml`) has been completely redesigned around the new consolidated scripts.

### Key Features

- **Simplified Matrix Strategy**: The workflow now uses a simple matrix to parallelize jobs by active single-model band (`goose`, `phish`, `wsp`, `billy`, `um`). The complex, hardcoded matrix for each band/model pair has been removed.
- **Streamlined Job**: The previous multi-job approach (`collect-data`, `generate-predictions`, `calculate-accuracy`) has been replaced by a single `daily-pipeline` job. This job contains sequential steps to run the full pipeline for each band, which is simpler to read and debug.
- **Declarative Steps**: The `run` steps now make direct, clean calls to the consolidated scripts, eliminating the need for conditional `if` logic within the YAML to select the correct script.

```yaml
# Example of the new, simplified workflow structure
jobs:
  daily-pipeline:
    strategy:
      matrix:
        band: [goose, phish, wsp]
    steps:
      - name: Run Data Collection
        run: python scripts/run_${{ matrix.band }}_collection.py

      - name: Generate Predictions
        run: |
          python scripts/generate_live_predictions.py --band ${{ matrix.band }}

      - name: Sync Retained Prediction Corpus
        run: |
          python scripts/sync_retained_prediction_corpus.py --band ${{ matrix.band }} --window 100 --incremental --require-results
```

## Performance and Efficiency

- **Simplified Accuracy Contract**: The active pipeline writes canonical
  per-show metrics to `setlist_accuracy` and validates replay lineage
  from `setlist_results`. Aggregate summary tables are no longer
  part of the active write path.
- **Data Reuse**: The local `run_optimized_pipeline.py` script still provides an efficient way to run the active single-model process locally for one band or all active bands.
- **Robust Error Handling**: The GitHub Actions workflow is configured with `fail-fast: false`, so a failure in one band's pipeline will not cancel the others.
