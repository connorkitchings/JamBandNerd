# Deal Model (ML-Based) — Logic and Historical Accuracy

### Overview

The Deal model is an ML-based predictor that uses gradient boosted trees to learn patterns in song rotation and provide probability rankings for songs being played. It is designed to coexist with the existing `notebook` and `ckplus` models as a third option, offering a different analytical perspective.

This model was inspired by the methodology in [twinfield10/Widespread-Panic-Setlists](https://github.com/twinfield10/Widespread-Panic-Setlists), which uses Deal binary classification with 100+ features. The JamBandNerd implementation adapts the spirit of that approach with a core feature set focused on temporal patterns, frequency metrics, and last-time-played features.

### Key Design Principles

- **Probabilistic Output**: Returns probability scores (0-1) for each candidate song
- **Temporal Awareness**: Uses multiple time windows (6mo, 1yr, 2yr, 4yr) to capture different rotation patterns
- **Class Imbalance Handling**: Addresses the fact that most songs in a show aren't played
- **Generalizable**: Band-agnostic core with configurable parameters per band
- **Hidden Until Approved**: Website visibility is controlled via configuration flag

### How it Runs

The Deal model is executed via the consolidated pipeline scripts. The primary method for running the full pipeline is the `run_optimized_pipeline.py` script, which handles data collection, transformation, and prediction generation for all models.

**Recommended: Full Pipeline**
```bash
# Run complete pipeline for any band (includes Deal model when enabled)
uv run python scripts/run_optimized_pipeline.py --band <band_name>
```

**Advanced: Individual Model Execution**
```bash
# Generate Deal predictions only
uv run python scripts/generate_predictions.py --band <band_name> --model xgboost
```

This will:

1. **Collect Data**: Fetch the latest show and setlist data for the specified band.
2. **Transform Data**: Prepare the raw data using the ModelData container.
3. **Generate Features**: Compute ML-specific features (temporal windows, frequency metrics, LTP features).
4. **Train/Update Model**: Retrain the Deal model if needed (model is persisted to disk).
5. **Generate Predictions**: Run the Deal model to generate probability-ranked predictions and save them to the database.

### Reference Show Date

- The model requires a reference show date: the show we are predicting.
- We resolve the reference to the latest `show_id` on that date.
- The last completed show is the most recent show with setlist data strictly before the reference date.
- **Critical**: All training and feature computation uses only data available strictly before the reference date to prevent data leakage.

### Inputs (from Supabase raw tables)

- `{band}_shows_raw(show_id, show_date, ...)`
- `{band}_setlists_raw(show_id, set_number, song_position, song_name, ...)`

### Feature Engineering

The Deal model uses a core feature set inspired by the WSP methodology. Features are computed per song relative to the reference date.

#### Temporal Window Features

For each song, compute counts and percentages across multiple time windows:

| Feature | Description |
|---------|-------------|
| `n_shows_6mo` | Number of shows where song was played in last 6 months |
| `n_shows_1yr` | Number of shows where song was played in last 1 year |
| `n_shows_2yr` | Number of shows where song was played in last 2 years |
| `n_shows_4yr` | Number of shows where song was played in last 4 years |
| `pct_shows_1yr` | Percentage of shows in 1-year window where song was played |
| `pct_shows_2yr` | Percentage of shows in 2-year window where song was played |

#### Frequency Features

| Feature | Description |
|---------|-------------|
| `total_plays` | Total historical plays across all time |
| `plays_past_year` | Total plays in past 365 days |
| `plays_past_2yr` | Total plays in past 730 days |
| `play_rate` | `plays_past_year / total_plays` ratio |

#### Last Time Played (LTP) Features

| Feature | Description |
|---------|-------------|
| `ltp_1` | Shows since last play (current gap) |
| `ltp_2` | Shows since 2nd-to-last play |
| `ltp_3` | Shows since 3rd-to-last play |
| `avg_ltp` | Average gap between plays |
| `recent_avg_ltp` | Average gap over last 25 plays |
| `overdue_metric` | `current_gap / avg_ltp` ratio |
| `ltp_trend` | `recent_avg_ltp - avg_ltp` (positive = playing more recently than average) |

#### Gap Statistics Features

| Feature | Description |
|---------|-------------|
| `std_gap` | Standard deviation of historical gaps |
| `min_gap` | Minimum historical gap |
| `max_gap` | Maximum historical gap |
| `gap_z_score` | `(current_gap - avg_gap) / std_gap` |

#### Context Features

| Feature | Description |
|---------|-------------|
| `current_gap` | Number of shows since last played |
| `last_played_date` | Date of last performance |
| `last_played_index` | Show index of last performance |
| `days_since_last` | Calendar days since last played |

### Training Data Generation

The model uses a binary classification approach where each (song, show) pair is labeled:

- **Positive class (1)**: Song was played at the show
- **Negative class (0)**: Song was not played at the show

Training is performed using a temporal train/test split:

1. **Training Window**: Use shows from `training_start` to `training_end`
2. **Test Window**: Use the most recent N shows (default: 50) for backtesting
3. **Feature Generation**: For each test show, generate features using only data available before that show

#### Class Imbalance Handling

Since most songs in a show aren't played (e.g., ~15-25 songs out of hundreds of candidates), the model addresses class imbalance via:

- `scale_pos_weight` parameter in Deal
- Or: undersampling negative class to match positive class ratio

### Model Configuration

Key hyperparameters (configurable per band):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_depth` | 6 | Maximum tree depth |
| `eta` | 0.1 | Learning rate |
| `nrounds` | 100 | Number of boosting rounds |
| `min_plays_threshold` | 5 | Minimum plays to include song as candidate |
| `retired_gap_threshold` | 150 | Exclude songs with gap > threshold |

### Ranking and Output

- Rank by probability score (descending), tie-break by song name (ascending)
- Output the top-K (default 50) prediction list with fields:
  - `song_name`: Song title
  - `probability`: Predicted probability (0-1)
  - `ltp`: Last time played (ISO date)
  - `current_gap`: Shows since last play
  - `plays_past_year`: Plays in last year
  - `times_played`: Total historical plays

### Historical Accuracy Measurement

We assess accuracy by iterating through historical show dates and treating each as the reference date:

1. For each show date `D`, generate predictions using only data available strictly before `D`.
2. Build the set of actual unique songs performed on date `D` from `{band}_setlists_raw`.
3. Compare predictions to actual using multiple metrics for K ∈ {10, 25, 50}:
   - hit_rate@K: proportion of shows with ≥1 predicted song in the actual set
   - avg_matches@K: average number of overlapping songs between top‑K and actual
   - precision@K: matches / K
   - recall@K: matches / |actual unique songs|
   - f1@K: harmonic mean of precision@K and recall@K
   - auc: Area under ROC curve (using actual binary labels)

### Reproducibility and Assumptions

- All features and training data are computed relative to the chosen reference date.
- The model never looks ahead of the reference date (strict temporal cutoff).
- Temporal window features use calendar time, not show indices.
- Model is persisted to disk and loaded for prediction on subsequent runs.
- Retraining occurs on each pipeline run (incremental or full retrain configurable).

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
  uv run python scripts/generate_predictions.py --band goose --model xgboost
  ```

- **Backtest over a window of show dates**:
  ```bash
  uv run python scripts/run_backtest.py --band goose --model xgboost --start YYYY-MM-DD --end YYYY-MM-DD
  uv run python scripts/run_backtest.py --band goose --model xgboost --shows 50
  ```

- **Save accuracy summary**:
  ```bash
  uv run python scripts/save_aggregate_accuracy.py --band goose --model xgboost --shows 50
  ```

### Storage

- Predictions: `predictions_xgboost` (upserted by `(band, reference_date, model_version)`).
- Per-song projection: `prediction_songs` (derived from canonical prediction rows).
- Accuracy summaries: `accuracy_xgboost` (band, model_version, window_start/window_end, metrics at K=10/25/50).
- Model artifacts: `models/xgboost_{band}_{date}.json` (Deal booster format)

### Website Visibility Control

The Deal model is hidden from the public website until explicitly approved. This is controlled via the `ENABLED_MODELS` configuration:

```python
# Default (xgboost hidden)
ENABLED_MODELS = ["notebook", "ckplus"]

# When approved (xgboost visible)
ENABLED_MODELS = ["notebook", "ckplus", "xgboost"]
```

The model is fully wired in the backend and generates predictions on each pipeline run, allowing for review via admin tools before public launch.

### Dependencies

The model requires:
- `xgboost>=2.0.0` (see `pyproject.toml`)

### Next Steps

- Implement core feature generation in `transformations/gaps.py` or new module
- Create `DealPredictor` class extending `PredictionModel`
- Wire into prediction pipeline scripts
- Run backtests and compare against Notebook and CK+ models
- Enable website visibility upon approval

### Rationale

The Deal model is designed to provide a data-driven alternative to the heuristic-based Notebook and CK+ models. Key design decisions:

- **Gradient Boosting**: Deal uses XGBoost, a powerful and efficient implementation of gradient boosted decision trees, well-suited for structured/tabular data.
- **Binary Classification**: The model learns to predict the probability of a song being played, providing a natural ranking via probability scores.
- **Core Features First**: Starting with temporal windows, frequency metrics, and LTP features allows for rapid iteration. Additional features (venue, city, state) can be added later if needed.
- **Temporal Split**: Using temporal train/test split ensures no data leakage and realistic accuracy estimates.
- **Probabilistic Output**: Unlike CK+ which returns raw scores, Deal outputs probabilities that can be calibrated and compared across songs.
