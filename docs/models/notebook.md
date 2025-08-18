## Notebook Model (Goose) — Logic and Historical Accuracy

### Overview

This document describes the baseline “notebook” model used to produce next‑show song predictions for Goose and how we measure historical accuracy. The model is intentionally simple and fast to compute directly from raw Supabase tables.

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
4. Exclude songs played in the last 3 completed shows (immediately before reference).
5. Compute for each song in window:
   - plays_past_year: count of plays in the window
   - last_played_show_index: index of most recent play in the window
   - current_gap: (reference_index − 1) − last_played_show_index

### Ranking and Output

- Rank primarily by `plays_past_year` (descending), tie‑break by `current_gap` (descending), then
  song name (ascending).
- Output the top‑50 as the prediction list with fields: `song_name`, `plays_past_year`, `current_gap`, `LTP` (last time played, mm/dd/yyyy).

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

### CLI Usage

- Generate next‑show predictions (defaults to today or next upcoming show):
  - `uv run python scripts/generate_goose_predictions.py`
  - With explicit reference date: `uv run python scripts/generate_goose_predictions.py --date YYYY-MM-DD`

- Backtest over a window of show dates:
  - `uv run python scripts/backtest_goose_notebook.py --start YYYY-MM-DD --end YYYY-MM-DD`
  - Outputs aggregate metrics for K=10/25/50.

- Save accuracy summary for the last 50 completed shows:
  - `uv run python scripts/save_notebook_accuracy.py`

### Storage

- Predictions: `goose_notebook_predictions` (upserted by `(band, reference_date, model_version)`).
- Accuracy summaries: `notebook_accuracy` (band, model_version, window_start/window_end, metrics at K=10/25/50).

### Next Steps

- Add configurable weighting that blends `plays_past_year` with contextual features (venue, tour, gap bands).
- Extend accuracy reporting with per‑era breakdowns and confidence intervals.
