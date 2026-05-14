# Goose Fast Predictor Experiment

## Goal

Apply the Billy fast-predictor lessons to Goose with an isolated compact
matrix-ranker challenger.

## Constraints

- Do not promote the challenger or change the Goose registry default.
- Preserve `goose_phase_b_v1` as the quality baseline.
- Keep the first fast pass compact and omit co-occurrence features.

## Commands Run

```bash
uv run pytest tests/models/test_goose_model.py -q
uv run ruff check src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run black src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run pytest tests/models/test_goose_model.py -q
uv run ruff check src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run python scripts/run_phase_b_backtest.py \
  --band goose \
  --predictor jambandnerd.models.goose.fast_predictor.GooseFastPredictor \
  --shows 100 \
  --snapshot-root .snapshots/goose_phase_b \
  --out-dir backtests/
time uv run python scripts/run_phase_b_backtest.py \
  --band goose \
  --predictor jambandnerd.models.goose.model.GoosePredictor \
  --shows 100 \
  --snapshot-root .snapshots/goose_phase_b \
  --out-dir backtests/
```

The final baseline timing command was interrupted after it had progressed far
enough to confirm the incumbent remains substantially slower. The completed
incumbent quality comparison uses the existing 100-show artifact.

## Files And Artifacts

- `src/jambandnerd/models/goose/fast_predictor.py`: added
  `GooseFastPredictor`, a Billy-style matrix LightGBM ranker.
- `src/jambandnerd/models/goose/__init__.py`: exported the experiment class.
- `tests/models/test_goose_model.py`: added defaults, band rejection,
  train/predict, recent-exclusion, and missing-venue tests.
- `backtests/goose_goose_fast_gbm_v1_summary.json`
- `backtests/goose_goose_fast_gbm_v1_100shows.jsonl`

## Validation

- Goose model tests passed: 12 tests.
- Ruff clean on Goose model files and tests.
- 100-show GooseFast backtest completed.

## Result

GooseFast is materially faster, but it missed the current quality baseline:

| Model | dual_score | F1@25 | p@10 | r@50 |
|---|---:|---:|---:|---:|
| `goose_phase_b_v1` | 0.399 | 0.270 | 0.265 | 0.534 |
| `goose_fast_gbm_v1` | 0.378 | 0.255 | 0.246 | 0.511 |

Do not promote. The compact matrix feature set appears underfit relative to the
current Deal-derived Goose baseline.

## Next Step

If continuing the fast path, add back Deal-derived signal incrementally and
measure the quality/runtime tradeoff. First candidates: all-time/one-year rate
features, gap z-score, and set-position features. Keep co-occurrence out until
the cheaper features are exhausted.
