# Billy Early Stopping Experiment — V6

## Goal

Add an isolated BillyFast early-stopping experiment before considering larger
architecture changes.

## Constraints

- Keep `BillyFastPredictorV3` as the production registry default unless the new
  variant beats V3 on `dual_score` or `p@10`.
- Preserve the existing V1-V5 experiment classes.
- Split validation by target-show group, not individual song rows.

## Commands Run

```bash
uv run pytest tests/models/test_billy_model.py -q
uv run black src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py
uv run ruff check src/jambandnerd/models/billy/fast_predictor.py tests/models/test_billy_model.py
uv run pytest tests/models/test_billy_model.py -q
uv run python scripts/run_phase_b_backtest.py \
  --band billy \
  --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictorV6 \
  --shows 100 \
  --snapshot-root .snapshots/billy_phase_b \
  --out-dir backtests/
```

## Files And Artifacts

- `src/jambandnerd/models/billy/fast_predictor.py`: added opt-in grouped
  LightGBM early stopping and `BillyFastPredictorV6`. V6 uses the holdout to
  select `best_iteration`, then refits on all training groups at that round
  count.
- `tests/models/test_billy_model.py`: added V6 feature, train/predict, and
  small-data fallback tests.
- `backtests/billy_billy_fast_gbm_v6_early_stop_summary.json`
- `backtests/billy_billy_fast_gbm_v6_early_stop_100shows.jsonl`

## Validation

- `tests/models/test_billy_model.py`: 25 passed.
- Ruff clean on touched Python files.
- V6 backtest over the same 100-show Billy snapshot completed with:
  - `dual_score=0.373`
  - `p@10=0.308`
  - `r@50=0.439`

## Result

V6 improved recall but missed the promotion gate versus the current V3 baseline
(`dual_score=0.377`, `p@10=0.322`, `r@50=0.432`). Registry and metadata were not
promoted; V3 remains the active Billy predictor.

## Next Step

Move to the larger Billy architecture experiment, likely two-stage ranking or a
blend with a simpler frequency/rotation model.
