# Deal Model Implementation

## Goal

Build a new ML-based prediction model using XGBoost that coexists with Notebook and CK+ models.

## Constraints

- Model must remain hidden from public website until explicit user approval
- Backend must be fully wired and generating predictions for review
- Training strategy: Option B - Persisted model with weekly retraining

## Implementation Status

### ✅ Completed

1. **Dependencies**
   - Added `xgboost>=2.0.0` to `pyproject.toml`

2. **Project Structure**
   - Created `src/jambandnerd/models/deal/` module
   - Created `models/deal/` directory for persisted models
   - Created `docs/reference/schemas/deal_tables.md` for SQL scripts

3. **Configuration**
   - Updated `src/jambandnerd/config/models.py`:
     - Added `MODEL_VERSIONS["deal"] = "deal_v1"`
     - Added `ENABLED_MODELS` (deal hidden initially)
     - Added Deal-specific config (DEAL_MIN_PLAYS_THRESHOLD, DEAL_RETIREMENT_GAP, etc.)
     - Added DEAL_RETRAIN_INTERVAL_DAYS = 7
   - Updated `src/jambandnerd/config/database.py`:
     - Added `PREDICTION_TABLES["deal"] = "predictions_deal"`
     - Added `ACCURACY_TABLES["deal"] = "accuracy_deal"`
   - Updated `src/jambandnerd/config/__init__.py` to export new config values

4. **Model Implementation**
   - Created `src/jambandnerd/models/deal/features.py`:
     - `generate_deal_features()`: Generate ML features per song
     - `generate_training_data()`: Create training data with labels
     - `get_candidate_features()`: Get candidate songs for prediction
   - Created `src/jambandnerd/models/deal/model.py`:
     - `DealPrediction` dataclass for output
     - `DealPredictor` class extending `PredictionModel`
     - `train()`: Train XGBoost model with weekly retraining logic
     - `predict()`: Generate probability-ranked predictions

5. **Serialization**
   - Updated `src/jambandnerd/models/serialization.py` to support Deal output format

6. **Pipeline Integration**
   - Updated `scripts/generate_predictions.py`:
     - Added "deal" to model choices
     - Added DealPredictor import and selection logic
     - Added `--retrain` flag for manual retrain
   - Updated `scripts/run_backtest.py`:
     - Added "deal" to model choices
     - Added DealPredictor import
     - Added training before prediction in backtest
   - Updated `scripts/save_aggregate_accuracy.py`:
     - Added "deal" to model choices

7. **Website Visibility Control**
   - Updated `apps/web/src/lib/config.ts`:
     - Added `deal` to MODEL_CONFIG with `enabled: false`
     - Updated ACTIVE_MODELS to only include enabled models

8. **Documentation**
   - Updated `docs/reference/models/xgboost.md`:
     - Added Implementation Status section
     - Added Pipeline Integration examples
     - Added Website Visibility Control section

## Commands Run

```bash
# Linting
uv run black src/jambandnerd/models/deal src/jambandnerd/config src/jambandnerd/models/serialization.py scripts/generate_predictions.py scripts/run_backtest.py scripts/save_aggregate_accuracy.py
uv run ruff check src/jambandnerd/models/deal src/jambandnerd/config scripts/generate_predictions.py scripts/save_aggregate_accuracy.py
```

## Next Step

Before running the model:
1. Run SQL statements in `docs/reference/schemas/deal_tables.md` to create Supabase tables
2. Test with: `uv run python scripts/generate_predictions.py --band goose --model deal`

## To Enable Public Website Visibility

Change `apps/web/src/lib/config.ts`:
```typescript
deal: {
  enabled: true, // Change from false to true
}
```
