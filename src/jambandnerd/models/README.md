# JamBandNerd Models Directory

This directory contains **band-agnostic** model logic and export utilities that can be used across
all bands (Phish, Goose, WSP, etc.).

## Architecture Overview

The models directory implements the separation of concerns principle:

- **`data_collection/`** - Only handles session data access (API calls, loaders) - NO export logic
- **`models/`** - Band-agnostic model logic and export methods (this directory)
- **`predictions/`** - Band-specific prediction pipelines with three responsibilities:
  1. **Data transformation** - Transform raw API data into model format
  2. **Model execution** - Use band-agnostic models from this directory
  3. **Prediction export** - Save predictions to Supabase using band-specific tables

## Modules

### Core Model Logic

- **`ckplus_model.py`** - CK+ (gap-based) model implementation
- **`notebook_model.py`** - Notebook model implementation with time-based filtering

### Export Utilities

- **`prediction_exporter.py`** - Band-agnostic prediction export logic for saving predictions to
  Supabase
- **`data_exporter.py`** - Band-agnostic data export utilities for saving raw data to Supabase

## Usage Examples

### Using CK+ Model

```python
from jambandnerd.models.ckplus_model import aggregate_setlist_features

# Prepare your setlist DataFrame with required columns:
# - song, show_index_overall, showdate, showid
predictions_df = aggregate_setlist_features(setlist_df, method="mean")
```

### Using Notebook Model

```python
from jambandnerd.models.notebook_model import aggregate_setlist_features
from datetime import datetime

# Prepare your setlist DataFrame with required columns:
# - song, showid, showdate
target_date = datetime.now()
predictions_df = aggregate_setlist_features(setlist_df, target_date)
```

### Saving Predictions

```python
from jambandnerd.models.prediction_exporter import save_predictions_to_supabase

# Save CK+ predictions
save_predictions_to_supabase(predictions_df, "phish_predictions_ckplus", "ckplus")

# Save notebook predictions
save_predictions_to_supabase(predictions_df, "goose_predictions_notebook", "notebook")
```

### Exporting Raw Data

```python
from jambandnerd.models.data_exporter import chunked_upsert_with_retry, prepare_dataframe_for_supabase

# Prepare DataFrame for Supabase
df_clean = prepare_dataframe_for_supabase(raw_df, "phish_songs")

# Export with chunked upsert
records = df_clean.to_dict(orient="records")
success = chunked_upsert_with_retry(
    supabase=supabase_client,
    table_name="phish_songs",
    records=records,
    on_conflict_col="songid"
)
```

## Benefits of This Architecture

1. **Code Reuse** - Model logic is shared across all bands
2. **Consistency** - All bands use the same prediction algorithms and export methods
3. **Maintainability** - Changes to model logic only need to be made in one place
4. **Testability** - Band-agnostic logic can be tested independently
5. **Scalability** - Adding new bands requires minimal code duplication

## Migration Notes

All existing prediction modules have been updated to use this band-agnostic logic:

- `src/jambandnerd/predictions/ckplus_model/phish/predict_today.py`
- `src/jambandnerd/predictions/ckplus_model/goose/predict_today.py`
- `src/jambandnerd/predictions/notebook_model/phish/predict_today.py`
- `src/jambandnerd/predictions/notebook_model/goose/predict_today.py`

Old band-specific model files (like `model.py` in each prediction directory) can be removed as they
are no longer used.
