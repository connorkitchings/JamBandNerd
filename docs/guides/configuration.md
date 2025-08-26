# Configuration Guide

This guide explains how to configure the JamBandNerd project, including how to add new bands and models, and how to set model parameters.

## Band Configuration

Adding a new band to the project requires changes in two main places: the data collection pipeline and the web application.

### 1. Data Collection

To add a new band, you need to create a new data collector for that band. The collectors are located in the `src/jambandnerd/data_collection/` directory.

1.  **Create a new collector**: Create a new file in `src/jambandnerd/data_collection/<band_name>/collector.py`. This file should contain a class that inherits from `BandCollector` and implements the required methods (`collect_shows`, `collect_setlists`, `collect_songs`, `collect_venues`).
2.  **Add to `run_optimized_pipeline.py`**: In `scripts/run_optimized_pipeline.py`, add the new band to the `CKPLUS_RETIREMENT_GAPS` dictionary and add a new `elif` block in the `run_band_pipeline` function to call your new collection script.

### 2. Web Application

To make the new band available in the Streamlit web application, you need to update the `BAND_CONFIG` dictionary in `src/jambandnerd/web/app.py`.

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

1.  **Create a new model**: Create a new file in `src/jambandnerd/models/<model_name>/model.py`. This file should contain a class that inherits from `PredictionModel` and implements the `predict` method.
2.  **Add prediction scripts**: Create new scripts in the `scripts/` directory to run your model and save the predictions and accuracy scores.

### 2. Web Application

To make the new model available in the Streamlit web application, you need to update the `MODEL_CONFIG` dictionary in `src/jambandnerd/web/app.py`.

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

## Model Parameters

Some models have parameters that can be configured. For example, the CK+ model has a `retired_gap_threshold` that can be set on a per-band basis.

This is currently configured in the `scripts/run_optimized_pipeline.py` script, in the `CKPLUS_RETIREMENT_GAPS` dictionary.

```python
CKPLUS_RETIREMENT_GAPS = {
    "goose": 100,
    "phish": 150,
}
```

To change the retirement gap for a band, you can simply update this dictionary.
