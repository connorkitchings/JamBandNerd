# Configuration Guide

This guide explains how to configure the JamBandNerd project, including how to add new bands and models, and how to set model parameters.

## Band Configuration

Adding a new band to the project requires changes in the data collection pipeline and, during the website transition, whichever presentation surfaces are still in use.

### 1. Data Collection

To add a new band, you need to create a new data collector and integrate it into the pipeline.

1. **Create Raw Tables**: In Supabase, create the necessary `_raw` tables for the new band (e.g., `wsp_shows_raw`, `wsp_setlists_raw`, etc.).
2. **Create a New Collector**: Create a new file in `src/jambandnerd/data_collection/<band_name>/collector.py`. This file should contain a class that inherits from `BandCollector` and implements the required methods (`collect_shows`, `collect_setlists`, `collect_songs`, `collect_venues`).
3. **Add to `run_optimized_pipeline.py`**: In `scripts/run_optimized_pipeline.py`, add a new `elif` block in the `run_band_pipeline` function to call your new collection script. You should also add a band-specific entry to the `CKPLUS_RETIREMENT_GAPS` dictionary.
4. **Update GitHub Actions**: In `.github/workflows/daily-pipeline.yml`, add the new band to the `matrix.band` list in the `collect-data` job and add a corresponding `elif` block to handle its collection script.

### 2. Presentation Layer

The long-term public surface is a website, not Streamlit. Today, the only repo-tracked UI configuration still lives in the legacy Streamlit app at `src/jambandnerd/web/app.py`. Update it only when you need interim parity before website cutover.

```python
BAND_CONFIG = {
    "goose": {
        "display_name": "Goose",
        "shows_table": "goose_shows_raw",
    },
    "phish": {
        "display_name": "Phish",
        "shows_table": "phish_shows_raw",
    },
    # Add your new band here
    "new_band": {
        "display_name": "New Band",
        "shows_table": "new_band_shows_raw",
    },
}
```

## Model Configuration

Adding a new model follows a similar pattern.

### 1. Model Implementation

1. **Create a new model**: Create a new file in `src/jambandnerd/models/<model_name>/model.py`. This file should contain a class that inherits from `PredictionModel` and implements the `predict` method.
2. **Add prediction scripts**: Create new scripts in the `scripts/` directory to run your model and save the predictions and accuracy scores.

### 2. Presentation Layer

The long-term public surface is a website, not Streamlit. Today, the only repo-tracked UI configuration still lives in the legacy Streamlit app at `src/jambandnerd/web/app.py`. Update it only when you need interim parity before website cutover.

```python
MODEL_CONFIG = {
    "notebook": {
        # ...
    },
    "ckplus": {
        # ...
    },
    # Add your new model here
    "new_model": {
        "display_name": "New Model",
        "explanation": "A brief explanation of how the new model works.",
        "columns": {
            # ... specify the columns to display for your model
        },
    },
}
```

## Model Parameter Tuning

Some models have parameters that can be configured to adjust their behavior. These are primarily located in `scripts/run_optimized_pipeline.py` and `src/jambandnerd/models/ckplus/model.py`.

### CK+ Model Parameters

The CK+ model is highly configurable. The key parameters are:

#### 1. Retirement Gap Threshold

This parameter, defined in the `CKPLUS_RETIREMENT_GAPS` dictionary in `scripts/run_optimized_pipeline.py`, sets the maximum `current_gap` a song can have before it is considered "retired" and excluded from predictions.

- **Why Tune It?** Bands have different rotation patterns. A band like Phish with a vast catalog may have longer gaps for non-retired songs compared to a band like Goose. Setting this on a per-band basis improves the model's accuracy by not prematurely excluding songs.
- **Example**:

  ```python
  CKPLUS_RETIREMENT_GAPS = {
      "goose": 100,  # A smaller gap for a band with a more regular rotation
      "phish": 150,  # A larger gap for a band with a deeper catalog
  }
  ```

#### 2. Alpha (`alpha`)

This parameter in the `CKPlusPredictor` class controls the weighting between the `gap_ratio` and the `gap_z_score` in the final score calculation.

- **Why Tune It?** A higher alpha gives more weight to the simple ratio of current gap to average gap, while a lower alpha gives more weight to the statistical significance (z-score). The default is `0.7`.

#### 3. Minimum Plays Threshold (`min_plays_threshold`)

This parameter in the `CKPlusPredictor` class sets the minimum number of times a song must have been played in the five-year window to be considered for prediction.

- **Why Tune It?** This prevents songs with very little historical data (and therefore unreliable gap statistics) from appearing in the predictions. The default is `5`.

### Notebook Model Parameters

The Notebook model has one key configurable parameter.

#### 1. Exclusion Window

This parameter, set via the `--exclusion-window` argument in the `generate_predictions.py` and `run_backtest.py` scripts, defines how many recent shows to look back when excluding songs from predictions.

- **Why Tune It?** Some bands rarely repeat songs within a short window, while others might. Adjusting this value allows you to fine-tune the model's recency filter. For example, setting it to `1` would only exclude songs from the very last show, while setting it to `5` would create a more aggressive filter.
- **Default**: `3`
