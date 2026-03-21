# Model Development Guide

This guide explains how to add a new prediction model to JamBandNerd. The pipeline is designed so that adding a model requires changes in exactly four places.

## Overview

A prediction model consumes the same `ModelData` handoff as all other models and produces a ranked list of song predictions. The canonical storage path writes to both a legacy row-per-run table and the unified `prediction_songs` projection table.

## Step-by-Step

### 1. Define the model class

**Location:** `src/jambandnerd/models/<newmodel>/model.py`

Create a directory under `src/jambandnerd/models/` and add a file containing your model class.

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.jambandnerd.models.base import PredictionModel
from src.jambandnerd.transformations.gaps import ModelData


@dataclass
class MyModelPrediction:
    """Define the fields this model exposes per song."""
    song_name: str
    # Add your model's specific fields here
    my_score: float


class MyModelPredictor(PredictionModel):
    """Describe what this model does."""

    def __init__(self, band: str | None = None):
        self.band = band

    def predict(
        self,
        model_data: ModelData,
        top_k: int = 50,
    ) -> tuple[List[MyModelPrediction], Dict[str, Any]]:
        """
        Generate top-K predictions.

        model_data gives you:
        - historical_plays: all plays before reference_date
        - master_feature_set: per-song aggregates (times_played, avg_gap, etc.)
        - reference_date: the cutoff date
        - reference_index: sequential show number
        - recently_played_songs: songs from the last N shows (exclusion window)

        Returns (predictions, diagnostics).
        """
        features = model_data.master_feature_set
        plays = model_data.historical_plays
        if features.empty or plays.empty:
            return [], model_data.diagnostics

        # TODO: implement your ranking logic
        ranked = features.sort_values(...).head(top_k)

        result: List[MyModelPrediction] = []
        for _, row in ranked.iterrows():
            result.append(MyModelPrediction(
                song_name=str(row["song_name"]),
                my_score=float(row["my_score"]),
            ))

        return result, model_data.diagnostics

    def train(self, data, *args, **kwargs) -> None:
        pass
```

Key rules:
- Inherit from `PredictionModel`
- `predict()` must accept `model_data: ModelData` and `top_k: int`
- `reference_date` is the anti-leakage cutoff — never use data after it
- `recently_played_songs` contains songs from the exclusion window; exclude them from predictions
- Return `(predictions, diagnostics)` where diagnostics is a dict for observability

### 2. Wire the model into the prediction script

**Locations:**
- `src/jambandnerd/models/__init__.py` — add your predictor to `__all__`
- `scripts/generate_predictions.py` — add import, instantiate, format, store

**In `scripts/generate_predictions.py`:**

Add the import near the top:
```python
from src.jambandnerd.models.newmodel.model import MyModelPredictor
```

Add model selection and formatting in `generate_predictions()`:
```python
elif model == "newmodel":
    predictor = MyModelPredictor(band=band)
    predictions = predictor.predict(model_data=model_data, top_k=50)
```

Add the output formatting block:
```python
elif model == "newmodel":
    predictions_list = [
        {
            "rank": i + 1,
            "song_name": p.song_name,
            # Flatten your model's fields here so they appear in the payload
            "my_score": p.my_score,
        }
        for i, p in enumerate(predictions)
    ]
    table_name = PREDICTION_TABLES["newmodel"]
    model_version = MODEL_VERSIONS["newmodel"]
```

### 3. Register the model version and table

**Location:** `src/jambandnerd/config/models.py`

```python
MODEL_VERSIONS: Final[dict[str, str]] = {
    "notebook": "notebook_v1",
    "ckplus": "ckplus_v1",
    "newmodel": "newmodel_v1",   # add this line
}
```

**Location:** `src/jambandnerd/config/database.py`

```python
PREDICTION_TABLES: Final[dict[str, str]] = {
    "notebook": "predictions_notebook",
    "ckplus": "predictions_ckplus",
    "newmodel": "predictions_newmodel",   # add this line
}
```

### 4. Add the model to the website

**Location:** `apps/web/src/lib/config.ts`

```typescript
export const MODEL_CONFIG = {
  notebook: {
    displayName: "Notebook",
    explanation: "Frequency-based model focused on songs active in the recent rotation...",
  },
  ckplus: {
    displayName: "CK+",
    explanation: "Gap-based model that ranks songs by how overdue they are...",
  },
  newmodel: {                           // add this block
    displayName: "My Model",
    explanation: "Description of what this model does.",
  },
} as const;
```

The website automatically handles the new model slug for `prediction_songs` reads and accuracy queries.

### 5. (Optional) Add CLI argument support

In `scripts/generate_predictions.py`, update the argparse choices:

```python
parser.add_argument(
    "--model",
    type=str,
    required=True,
    choices=["notebook", "ckplus", "newmodel"],   # add "newmodel"
    help="The model to use for predictions.",
)
```

### 6. (Optional) Add accuracy calculation

If you want per-show accuracy metrics for your model, add the accuracy computation to `src/jambandnerd/models/accuracy.py` following the same pattern as `compute_notebook_metrics` / `compute_ckplus_metrics`.

## Storage Path

Once wired, predictions are stored via `replace_prediction_projection()` in `db/operations.py`, which writes to `prediction_songs` with the `model_slug` set to your new model name. This means the website and all analytics queries that read from `prediction_songs` will automatically include your new model without additional changes.

## Testing

Run the prediction for a single band to verify:
```bash
uv run python scripts/generate_predictions.py --band goose --model newmodel
```

Run backtests:
```bash
uv run python scripts/run_backtest.py --band goose --model newmodel --shows 50
```

Check the output:
```bash
uv run python scripts/validate_prediction_tables.py --band goose --model newmodel
```
