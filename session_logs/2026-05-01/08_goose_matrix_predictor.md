# Goose Matrix Predictor — Clean-Slate Quality Recovery

## Goal

Try a clean-slate Goose challenger that keeps the Billy-style fast matrix
architecture but adds back cheap Deal-derived quality signals.

## Constraints

- Do not promote unless it beats `goose_phase_b_v1`.
- Avoid full co-occurrence in this pass.
- Preserve `GooseFastPredictor` as the compact fast baseline.

## Commands Run

```bash
uv run pytest tests/models/test_goose_model.py -q
uv run ruff check src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run black src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run pytest tests/models/test_goose_model.py -q
uv run ruff check src/jambandnerd/models/goose tests/models/test_goose_model.py
uv run python scripts/run_phase_b_backtest.py \
  --band goose \
  --predictor jambandnerd.models.goose.fast_predictor.GooseMatrixPredictor \
  --shows 100 \
  --snapshot-root .snapshots/goose_phase_b \
  --out-dir backtests/
```

An initial matrix backtest was stopped after the first few shows because the
set-position implementation recomputed historical aggregates too often. It was
reworked to cumulative set-position matrices before the completed run.

## Files And Artifacts

- `src/jambandnerd/models/goose/fast_predictor.py`: added
  `GooseMatrixPredictor`, cumulative set-position matrices, and matrix versions
  of Deal-like gap/rate features.
- `src/jambandnerd/models/goose/__init__.py`: exported matrix feature columns
  and predictor.
- `tests/models/test_goose_model.py`: added matrix defaults, train/predict, and
  missing venue/set-position fallback tests.
- `backtests/goose_goose_matrix_gbm_v1_summary.json`
- `backtests/goose_goose_matrix_gbm_v1_100shows.jsonl`

## Validation

- Goose model tests passed: 15 tests.
- Ruff clean on Goose model files and tests.
- 100-show GooseMatrix backtest completed.

## Result

The added cheap features did not recover the incumbent quality gap:

| Model | dual_score | F1@25 | p@10 | r@50 |
|---|---:|---:|---:|---:|
| `goose_phase_b_v1` | 0.399 | 0.270 | 0.265 | 0.534 |
| `goose_fast_gbm_v1` | 0.378 | 0.255 | 0.246 | 0.511 |
| `goose_matrix_gbm_v1` | 0.377 | 0.258 | 0.244 | 0.510 |

Do not promote. The matrix architecture is fast, but the current cheap feature
blocks are not enough for Goose quality.

## Next Step

Stop adding cheap matrix features. Next Goose attempt should test a genuinely
different signal: selective/recency-weighted co-occurrence, reciprocal-rank
fusion with the incumbent, or an optimized incumbent logistic path.
