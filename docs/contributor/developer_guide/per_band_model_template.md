# Per-Band Model Template (Phase B)

This guide explains how to add a new specialized predictor for a band under the
single-model-per-band architecture (ADR 0001).

## Directory Layout

```
src/jambandnerd/models/{band}/
├── __init__.py        # re-exports the predictor class
├── model.py           # {Band}Predictor — subclasses DealPredictor or BandGbmPredictor
└── features.py        # OPTIONAL: band-specific feature additions

tests/models/
└── test_{band}_model.py  # registry wiring + smoke train/predict + leakage guard
```

`goose/` is the canonical example. Copy it as a starting point.

## Predictor Families

Choose based on backtest results — both implement `PredictionModel` and return
`List[DealPrediction]`, so the existing Deal serializer (`get_band_serializer`)
works for both.

### Family A — Logistic (`DealPredictor`)

```python
from jambandnerd.models.deal.model import DealPredictor

PHISH_FEATURE_COLUMNS: list[str] = [...]  # subset of DEAL_FEATURE_COLUMNS

class PhishPredictor(DealPredictor):
    MODEL_DIR = Path("models/phish")
    MODEL_VERSION = "phish_phase_b_v1"

    def __init__(self, band: str = "phish", **kwargs):
        if band != "phish":
            raise ValueError("PhishPredictor only supports band='phish'.")
        defaults = {
            "min_plays_threshold": 5,
            "retired_gap_threshold": 150,
            "training_window_shows": 75,
            "min_training_shows": 25,
            "feature_columns": list(PHISH_FEATURE_COLUMNS),
        }
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)
```

### Family B — GBM (`BandGbmPredictor`)

```python
from jambandnerd.models.gbm.predictor import BandGbmPredictor

class PhishGbmPredictor(BandGbmPredictor):
    MODEL_VERSION = "phish_phase_b_v1_gbm"

    def __init__(self, band: str = "phish", **kwargs):
        if band != "phish":
            raise ValueError("PhishGbmPredictor only supports band='phish'.")
        defaults = {"n_estimators": 150, "num_leaves": 63}
        defaults.update(kwargs)
        super().__init__(band=band, **defaults)
```

## Registering the Model

1. Add the predictor class to `src/jambandnerd/models/registry.py`:

```python
from jambandnerd.models.phish.model import PhishPredictor

_BAND_PREDICTOR_CLASSES: dict[str, type[PredictionModel]] = {
    "goose": GoosePredictor,
    "phish": PhishPredictor,  # new
}
```

2. Add a `BandMetadata` entry to `src/jambandnerd/models/metadata.py`:

```python
BAND_METADATA: list[BandMetadata] = [
    BandMetadata(band="goose", model_version="goose_phase_b_v1", default_top_k=25),
    BandMetadata(band="phish", model_version="phish_phase_b_v1", default_top_k=25),
    ...
]
```

## Evaluation Protocol

Evaluate on the last 100 completed shows with a walk-forward backtest.
The dual objective is **precision@10** (head of the list) and **recall@50**
(long-list coverage), combined into a single scalar:

```
dual_score = 0.5 · p@10 + 0.5 · r@50
```

Override the alpha per band in `config/models.py:BAND_DUAL_OBJECTIVE_ALPHA`.

Run the backtest:

```bash
uv run python scripts/run_backtest.py --band phish --shows 100 --dry-run
```

The output includes a `DUAL OBJECTIVE` summary line with `p@10`, `r@50`,
`dual`, and `weighted_p`.

## Promotion Gate

Compare the candidate to the incumbent using `is_band_promotion_eligible`
from `src/jambandnerd/models/readiness.py`. Default thresholds:

- `min_p10_delta = 0.02` (+2pp absolute precision@10)
- `min_r50_delta = 0.02` (+2pp absolute recall@50)
- `min_shows = 100`

Both metrics must improve. No Pareto regression in either direction is allowed.

## Tests

Minimum test coverage (`tests/models/test_{band}_model.py`):

1. Predictor instantiates with correct defaults.
2. Predictor rejects other band names.
3. Smoke: `train` + `predict` on a synthetic fixture produces non-empty,
   deduplicated predictions.
4. Leakage: no actual-show songs appear in historical data at `reference_date`.
5. Registry: `build_band_predictor(band)` returns the expected class.

Run the per-band framework contract tests:

```bash
uv run pytest tests/models/test_per_band_template.py
```

These are parameterized over `ACTIVE_BANDS` and fail automatically if
registration or metadata is missing.

## Feature Engineering

Band-specific features go in `models/{band}/features.py` and must:

- Compute strictly from `historical_plays` with `show_date < reference_date`.
- Return columns that can be appended to the `DEAL_FEATURE_COLUMNS` set.
- Have a leakage regression test.

Candidate features to consider per band:

| Feature | Relevance |
|---|---|
| `show_position_in_run` | Multi-night runs change song repeat probability |
| `days_since_last_show` | Long breaks shift the rotation |
| `dow_play_rate` (song × day-of-week) | Weekend vs midweek setlists differ |
| `month_play_rate` (song × month) | Seasonal patterns |
| `set_position_prior` (set1/set2/encore) | Set placement is highly informative |
