# CK+ Model (Gap-Based) — Logic and Historical Accuracy

### Overview

The CK+ model is a gap-based statistical predictor that ranks songs by how "overdue" they are to be
played, using historical show-to-show gaps between performances. It is intentionally simple, fast,
and explainable, and complements the frequency‑based `notebook` model.

### How it Runs

The CK+ model is executed via the consolidated pipeline scripts. The primary method for running the full pipeline is the `run_optimized_pipeline.py` script, which handles data collection, transformation, and prediction generation for all models.

**Recommended: Full Pipeline**
```bash
# Run complete pipeline for any band (includes CK+ model)
uv run python scripts/run_optimized_pipeline.py --band <band_name>
```

**Advanced: Individual Model Execution**
```bash
# Generate CK+ predictions only
uv run python scripts/generate_predictions.py --band <band_name> --model ckplus
```

This will:

1. **Collect Data**: Fetch the latest show and setlist data for the specified band.
2. **Transform Data**: Prepare the raw data using the ModelData container.
3. **Generate Predictions**: Run the CK+ model to generate predictions and save them to the database.

### Reference Show Date

- The model requires a reference show date: the show we are predicting.
- We resolve the reference to the latest `show_id` on that date.
- The last completed show is the most recent show with setlist data strictly before the reference
  date.

### Inputs (from Supabase raw tables)

- `goose_shows_raw(show_id, show_date, ...)`
- `goose_setlists_raw(show_id, set_number, song_position, song_name, ...)`

### Transformation and Features

Given a reference show date:

1. Compute a sequential `show_index` over all shows ordered by `show_date`, tie‑broken by `show_id`.
2. Determine the last completed show (by setlists strictly before reference) and its index.
3. Define a five‑year window as `[last_completed_date − 5×365 days, last_completed_date]`.
4. For each song, compute gap statistics using only plays within that 5‑year window. Compute the
   following per song:
   - `times_played`: total plays in the 5‑year window
   - `ltp_date`: last time played within the 5‑year window (ISO date from the most recent completed
     show strictly before reference)
   - `current_gap`: number of shows since last play relative to the reference index, i.e.,
     `(reference_index − 1) − last_played_show_index`
   - `avg_gap`: mean of historical gaps between consecutive plays
   - `std_gap`: standard deviation of historical gaps (with small‑sigma guard to avoid divide‑by‑zero)
   - `gap_ratio`: `current_gap / avg_gap` (higher means more overdue relative to typical)
   - `gap_z_score`: `(current_gap − avg_gap) / std_gap` when `std_gap > 0`, else 0
   - `ckplus_score` (ckplus_v1): overdue score with reliability scaling (see formula below)

5. Apply filters:
   - Minimum data: exclude songs with `times_played <= 2` in the 5‑year window (insufficient history)
   - Exclude recently played: exclude `current_gap ∈ {0, 1}`
   - Retired heuristic: exclude songs with `current_gap > retired_gap_threshold_by_band`
     (configurable per band)
   - For Widespread Panic, exclude "Jam" and "Drums" from the candidates.
   - Exclude rows with undefined math (e.g., missing `avg_gap`, non‑finite values)

#### Scoring Formula (ckplus_v1)

- Let `alpha` be a weighting parameter in [0, 1].
- Define the reliability term `R`:
  - `R = min(1.0, times_played / min_plays_threshold_by_band) * (1.0 / (1.0 + std_gap))`
- Define the base overdue signal `S`:
  - `S = alpha * gap_ratio + (1 - alpha) * max(0, gap_z_score)`
- Final score:
  - `ckplus_score = S * R`

Notes:

- `min_plays_threshold_by_band` and `retired_gap_threshold_by_band` are band‑specific configuration values.
- Suggested defaults will be set per band; values to be finalized in configuration.

### Ranking and Output

- Rank primarily by `ckplus_score` (descending), tie‑break by `gap_ratio` (descending), then song
  name (ascending).
- Output the top‑K (default 50) prediction list with fields: `song_name`, `times_played`,
  `ltp_date` (mm/dd/yyyy), `current_gap`, `avg_gap`, `gap_ratio`, `gap_z_score`, `ckplus_score`.

### Historical Accuracy Measurement

We assess accuracy by iterating through historical show dates and treating each as the reference date:

1. For each show date `D`, generate predictions using only data available strictly before `D`.
2. Build the set of actual unique songs performed on date `D` from `goose_setlists_raw`.
3. Compare predictions to actual using multiple metrics for K ∈ {10, 25, 50}:
   - hit_rate@K: proportion of shows with ≥1 predicted song in the actual set
   - avg_matches@K: average number of overlapping songs between top‑K and actual
   - precision@K: matches / K
   - recall@K: matches / |actual unique songs|
   - f1@K: harmonic mean of precision@K and recall@K

### Reproducibility and Assumptions

- Gap calculations are over show indices (not calendar time).
- Filters and the 5‑year statistics window are applied relative to the chosen reference date and
  last completed show.
- The retired‑song and minimum‑plays thresholds are band‑specific and versioned.
- The `ckplus_score` formula is versioned; it blends overdue magnitude (`gap_ratio` and
  `gap_z_score`) with reliability scaling.
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
  uv run python scripts/generate_predictions.py --band goose --model ckplus
  uv run python scripts/generate_predictions.py --band phish --model ckplus
  ```

- **Backtest over a window of show dates**:
  ```bash
  uv run python scripts/run_backtest.py --band goose --model ckplus --start YYYY-MM-DD --end YYYY-MM-DD
  uv run python scripts/run_backtest.py --band goose --model ckplus --shows 50
  ```

- **Save accuracy summary**:
  ```bash
  uv run python scripts/save_aggregate_accuracy.py --band goose --model ckplus --shows 50
  ```

### Storage

- Predictions: `predictions_ckplus` (upserted by `(band, reference_date, model_version)`).
- Accuracy summaries: `accuracy_ckplus` (band, model_version, window_start/window_end, metrics at K=10/25/50).

#### Validation RPC

We use a simple RPC to fetch table schemas for validation:

```sql

create or replace function public.get_table_schema(p_table_name text)
returns table (column_name text, data_type text, is_nullable text)
language sql as $
  select column_name, data_type, is_nullable
  from information_schema.columns
  where table_schema = 'public' and table_name = p_table_name
  order by ordinal_position;
$;
grant execute on function public.get_table_schema(text) to anon, authenticated, service_role;

```

- Each prediction row contains an array of objects with fields: `rank`, `song_name`, `times_played`,
   `current_gap`, `avg_gap`, `gap_ratio`, `gap_z_score`, `ckplus_score`, `LTP` (mm/dd/yyyy).

### Open Questions / Clarifications Needed

- Numeric configuration per band: `min_plays_threshold_by_band` and `retired_gap_threshold_by_band`
  values.
- Preferred default `alpha` for ckplus_v1 (e.g., 0.6–0.8 range) and whether to cap `gap_ratio` or `gap_z_score`.
- Use 5×365 days vs calendar 5 years (leap years) for the window definition.

### Next Steps

- Finalize v1 `ckplus_score` weighting and thresholds; document as `model_version = ckplus_v1`.
- Implement scripts and backtesting to populate `predictions_ckplus` and `accuracy_ckplus`.
- Add per‑era breakdowns and confidence intervals similar to the notebook model.
- Compare `notebook` vs `ckplus` performance in the UI and consider blended scoring.

### Rationale

The CK+ model is designed to provide a different perspective from the frequency-based Notebook model. It is based on the idea that songs that haven't been played in a while are more likely to be played soon.

- **Gap-Based**: The model's core logic is based on the concept of "gaps" between song performances. This provides a strong signal for songs that are "due" for a performance.
- **Reliability Scaling**: The model includes a reliability term that scales the overdue signal by the number of times a song has been played and the standard deviation of its gaps. This helps to prevent songs with very few plays or erratic histories from being ranked too highly.
- **Five-Year Window**: The five-year window for calculating gap statistics is a heuristic that provides a long-term view of a song's performance history. This is in contrast to the Notebook model's one-year window, which focuses on more recent trends.
- **Configurable Thresholds**: The model includes configurable thresholds for minimum plays and retirement gaps, which allows for band-specific tuning.
