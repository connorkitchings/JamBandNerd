# Extending the Platform

This guide explains how to add new bands and models to the JamBandNerd project.

## How to Add a New Band

Adding a new band to the project requires changes in the data collection pipeline and, during the website transition, whichever presentation surfaces are still in use.

### 1. Data Collection

To add a new band, you need to create a new data collector and integrate it into the pipeline.

1. **Create Raw Tables**: In Supabase, create the necessary `_raw` tables for the new band (e.g., `wsp_shows_raw`, `wsp_setlists_raw`, etc.).
2. **Create a New Collector**: Create a new file in `src/jambandnerd/data_collection/<band_name>/collector.py`. This file should contain a class that inherits from `BandCollector` and implements the required methods (`collect_shows`, `collect_setlists`, `collect_songs`, `collect_venues`).
3. **Add to `run_optimized_pipeline.py`**: In `scripts/run_optimized_pipeline.py`, add a new `elif` block in the `run_band_pipeline` function to call your new collection script. You should also add a band-specific entry to the `CKPLUS_RETIREMENT_GAPS` dictionary.
4. **Update GitHub Actions**: In `.github/workflows/daily-pipeline.yml`, add the new band's slug (e.g., `new_band`) to the `matrix.band` list. The workflow will automatically call the correct collection script (`run_new_band_collection.py`) without needing any other changes.

### 2. Presentation Layer

The public surface is the website app in `apps/web`. Add new bands to `apps/web/src/lib/config.ts`. Update the legacy Streamlit fallback only if you explicitly need temporary parity during cutover.

```ts
BAND_CONFIG = {
  goose: {
    displayName: "Goose",
    showsTable: "goose_shows_raw",
  },
  new_band: {
    displayName: "New Band",
    showsTable: "new_band_shows_raw",
  },
} as const;
```

## How to Add a New Model

Adding a new model follows a similar pattern.

### 1. Model Implementation

1. **Create a new model**: Create a new file in `src/jambandnerd/models/<model_name>/model.py`. This file should contain a class that inherits from `PredictionModel` and implements the `predict` method.

2. **Update consolidated scripts**: Instead of creating individual scripts, update the existing consolidated scripts to support your new model:
   - Add your model to the choices in `scripts/generate_predictions.py`
   - Add your model to the choices in `scripts/run_backtest.py`
   - Add your model to the choices in `scripts/save_aggregate_accuracy.py`
   - Update `scripts/run_optimized_pipeline.py` to include your new model in the pipeline

3. **Create prediction table**: Create a new Supabase table `predictions_<model_name>` to store predictions.

4. **Create accuracy table**: Create a new Supabase table `accuracy_<model_name>` to store accuracy metrics.

### 2. Presentation Layer

The public surface is the website app in `apps/web`. Add new models to `apps/web/src/lib/config.ts`. Update the legacy Streamlit fallback only if you explicitly need temporary parity during cutover.

```ts
MODEL_CONFIG = {
  notebook: {
    displayName: "Notebook",
    explanation: "Existing notebook model explanation.",
  },
  new_model: {
    displayName: "New Model",
    explanation: "A brief explanation of how the new model works.",
  },
} as const;
```
