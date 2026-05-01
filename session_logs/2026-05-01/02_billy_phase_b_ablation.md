# Billy Phase B Ablation — BillyFastPredictorV2

## Goal

Add all 4 non-sparse Phase B candidate features to the production BillyFast model and
verify they improve dual_score over v1 (0.366).

## Features Added (v2 vs v1)

| Feature | How computed |
|---------|-------------|
| `tour_position` | Shows in current tour stretch (gap < 14 days) via `_tour_position()` |
| `diff_25_to_50` | `pct_plays_past_25 - pct_plays_past_50` (from presence matrix, free) |
| `show_position_in_run` | Night in consecutive run (gap ≤ 1 day) via `_run_position()` |
| `same_venue_run_position` | Prior shows at same venue in current run + 1; 0 if no venue |

Excluded (96.8% sparse, zero gain in diagnostic): `same_venue_run_prior_play_count`,
`same_venue_run_prior_play_share`, `same_venue_run_prior_played`.

## Implementation

- `src/jambandnerd/models/billy/fast_predictor.py`:
  - Added `BILLY_FAST_V2_FEATURE_COLS` constant (11 features)
  - Added `_FEATURE_COLS` class attribute + `col_dates`/`col_venues` to `_prepare()` cache
  - Added `_extra_training_row_features()` and `_extra_predict_features()` extension hooks
    to `BillyFastPredictor` (no-op in v1)
  - Modified `train()` and `predict()` to call hooks and use `self._FEATURE_COLS`
  - Added `BillyFastPredictorV2` subclass overriding the hooks and `MODEL_VERSION`
- `src/jambandnerd/models/registry.py`: updated default from v1 → v2
- `tests/models/test_billy_model.py`: added 4 v2 tests, updated registry assertion

## Backtest Results (100 shows, 2025-02-14 – 2026-04-18)

| Model | dual_score | p@10 | r@50 |
|---|---|---|---|
| GBM v1 (baseline) | 0.366 | 0.308 | 0.425 |
| **GBM v2 (promoted)** | **0.374** | **0.327** | 0.422 |

- dual_score: +0.008 (+2.2%)
- p@10: +0.019 (+6.2%) — meaningful improvement
- r@50: −0.003 (−0.7%) — within noise

## Commands Run

```bash
uv run pytest tests/models/test_billy_model.py -q
uv run python scripts/run_phase_b_backtest.py \
  --band billy \
  --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictorV2 \
  --shows 100 \
  --snapshot-root .snapshots/billy_phase_b \
  --out-dir backtests/
uv run black src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py
uv run ruff check src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py
```

## Decision

v2 promoted to production default. v1 (`BillyFastPredictor`) retained in code as parent
class — delete if no longer needed.

## Next Steps

- If further improvement is desired: try LightGBM HP tuning on v2
  (num_leaves 31→63, rounds 200→400, add reg_alpha/reg_lambda=0.1)
- Artifact: `backtests/billy_billy_fast_gbm_v2_summary.json`
