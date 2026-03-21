# Notebook Model (Goose) — Logic and Historical Accuracy

### Overview

This document describes the baseline “notebook” model used to produce next‑show song predictions for
Goose and how we measure historical accuracy. The model is intentionally simple and fast to
compute directly from raw Supabase tables.

### How it Runs

The Notebook model is executed via the consolidated pipeline scripts. The primary method for running the full pipeline is the `run_optimized_pipeline.py` script, which handles data collection, transformation, and prediction generation for all models.

**Recommended: Full Pipeline**
```bash
# Run complete pipeline for any band (includes Notebook model)
uv run python scripts/run_optimized_pipeline.py --band <band_name>
```

**Advanced: Individual Model Execution**
```bash
# Generate Notebook predictions only
uv run python scripts/generate_predictions.py --band <band_name> --model notebook
```

This will:

1. **Collect Data**: Fetch the latest show and setlist data for the specified band.
2. **Transform Data**: Prepare the raw data using the ModelData container.
3. **Generate Predictions**: Run the Notebook model to generate predictions and save them to the database.

### Reference Show Date

- The model requires a reference show date: the show we are predicting.
- We resolve the reference to the latest `show_id` on that date.
- The last completed show is the most recent show with setlist data strictly before the reference date.

### Inputs (from Supabase raw tables)

- `goose_shows_raw(show_id, show_date, ...)`
- `goose_setlists_raw(show_id, set_number, song_position, song_name, ...)`

### Transformation and Features

Given a reference show date:

1. Determine the last completed show (by setlists strictly before reference).
2. Define last‑year window as [last_completed_date − 365 days, last_completed_date].
3. Restrict plays to that window (hard rule: only last‑year plays count).
4. Exclude songs played in the last N completed shows (default is 3, but this window is configurable when running the prediction scripts).
5. For Widespread Panic, exclude "Jam" and "Drums" from the candidates.
6. Compute for each song in window:
   - plays_past_year: count of plays in the window
   - last_played_show_index: index of most recent play in the window
   - current_gap: (reference_index − 1) − last_played_show_index

### Ranking and Output

- Rank primarily by `plays_past_year` (descending), tie‑break by `current_gap` (descending), then
  song name (ascending).
- Output the top‑50 as the prediction list with fields: `song_name`, `plays_past_year`,
  `current_gap`, `LTP` (last time played, mm/dd/yyyy).

### Historical Accuracy Measurement

We assess accuracy by iterating through historical show dates and treating each as the reference date:

1. For each show date `D`, generate predictions (top‑50) using only data available strictly
   before `D`.
2. Build the set of actual unique songs performed on date `D` from `goose_setlists_raw`.
3. Compare predictions to actual using multiple metrics for K ∈ {10, 25, 50}:
   - hit_rate@K: proportion of shows with ≥1 predicted song in the actual set
   - avg_matches@K: average number of overlapping songs between top‑K and actual
   - precision@K: matches / K
   - recall@K: matches / |actual unique songs|
   - f1@K: harmonic mean of precision@K and recall@K

### Reproducibility and Assumptions

- All windows and exclusions are relative to the chosen reference date.
- Last‑year policy is strict; songs not played in the window are ineligible.
- The last‑3 exclusion uses the three completed shows immediately before the reference date.
- The model never looks ahead of the reference date.

### Pipeline Usage

The recommended way to run the pipeline is with the `run_optimized_pipeline.py` script, which handles data collection, transformations, and predictions for all models.

- **Run the full pipeline for a specific band**:

  ```bash
  uv run python scripts/run_optimized_pipeline.py --band goose
  ```

- **Run without accuracy calculations for speed**:

  ```bash
  uv run python scripts/run_optimized_pipeline.py --band goose --skip-accuracy
  ```

For debugging or granular control, you can use the consolidated individual scripts:

- **Generate predictions for any band/model combination**:
  ```bash
  uv run python scripts/generate_predictions.py --band goose --model notebook
  uv run python scripts/generate_predictions.py --band phish --model notebook
  ```

- **Backtest over a window of show dates**:
  ```bash
  uv run python scripts/run_backtest.py --band goose --model notebook --start YYYY-MM-DD --end YYYY-MM-DD
  uv run python scripts/run_backtest.py --band goose --model notebook --shows 50
  ```

- **Save accuracy summary**:
  ```bash
  uv run python scripts/save_aggregate_accuracy.py --band goose --model notebook --shows 50
  ```

### Storage

- Predictions: `predictions_notebook` (upserted by `(band, reference_date, model_version)`).
- Per-song projection: `prediction_songs` (derived from canonical prediction rows).
- Accuracy summaries: `notebook_accuracy` (band, model_version, window_start/window_end, metrics at K=10/25/50).

### Next Steps

- Add configurable weighting that blends `plays_past_year` with contextual features (venue, tour,
  gap bands).
- Extend accuracy reporting with per‑era breakdowns and confidence intervals.

### Rationale

The Notebook model is designed to be a simple, transparent, and effective baseline for setlist prediction. Here are the reasons behind some of its key design decisions:

- **Frequency-Based**: The model's core logic is based on the simple assumption that songs played frequently in the recent past are more likely to be played again soon. This is a common pattern for many touring bands and provides a solid foundation for prediction.
- **One-Year Window**: The one-year window for counting plays is a heuristic that balances recency and a large enough sample size. It ensures that the model is responsive to changes in a band's rotation while still capturing a meaningful amount of data.
- **Last-Three-Show Exclusion**: The exclusion of songs played in the last three shows is a common-sense rule to avoid predicting songs that have been played very recently. This is a simple but effective way to improve the model's accuracy.
- **Simplicity and Speed**: The model is intentionally simple so that it is easy to understand, implement, and maintain. Its speed also allows for rapid backtesting and iteration.
