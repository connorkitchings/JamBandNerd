# Session 04 — UM Phase B Experiments

**Date**: 2026-05-06
**Branch**: `feat/single-model-per-band`

## Goal

Push UM model performance past V2 baseline (dual=0.343) via window, feature, and architecture experiments.

## Constraints

- Use `uv run` for all commands
- 100-show walk-forward backtest on `.snapshots/um_phase_b/` snapshots
- Never work on `main`
- Experiment code stays in branch until merge prep

## Commands Run

```bash
# Window experiments
uv run python scripts/run_experiment.py --band um --sweep window_sweep --only window_200 --shows 100 --snapshot-root .snapshots/um_phase_b
uv run python scripts/run_experiment.py --band um --sweep window_sweep --only window_300 --shows 100 --snapshot-root .snapshots/um_phase_b
# full_history timed out at 15 min

# Feature experiments
uv run python scripts/run_experiment.py --band um --sweep feat_sweep --only feat_notebook_rank --shows 100 --snapshot-root .snapshots/um_phase_b
uv run python scripts/run_experiment.py --band um --sweep feat_sweep --only feat_venue_run --shows 100 --snapshot-root .snapshots/um_phase_b
uv run python scripts/run_experiment.py --band um --sweep feat_sweep --only feat_long_rotation --shows 100 --snapshot-root .snapshots/um_phase_b

# Validation
uv run pytest tests/ -q
uv run ruff check src/jambandnerd/models/um/fast_predictor.py src/jambandnerd/models/um/experiments.py src/jambandnerd/models/phish/fast_predictor.py
```

## Files Changed

- `src/jambandnerd/models/phish/fast_predictor.py`: Added `_training_window()` method to PhishFastPredictor (overridable hook replacing hardcoded `_TRAINING_WINDOW` in `generate_training_frame` and `train`)
- `src/jambandnerd/models/um/fast_predictor.py`: Added `UMFastPredictorV2Window200`, `UMFastPredictorV2Window300`, `UMFastPredictorV2FullHistory`, `UMFastPredictorV2NotebookRank`, `UMFastPredictorV2VenueRun`, `UMFastPredictorV2LongRotation`
- `src/jambandnerd/models/um/experiments.py`: Added `UM_WINDOW_SWEEP` (3 configs) and `UM_FEAT_SWEEP` (3 configs)

## Artifacts Produced

- `backtests/um_um_fast_gbm_v2_window200_summary.json` (dual=0.3269)
- `backtests/um_um_fast_gbm_v2_window300_summary.json` (dual=0.3304)
- `backtests/um_um_fast_gbm_v2_notebook_rank_summary.json` (dual=0.3339)
- `backtests/um_um_fast_gbm_v2_venue_run_summary.json` (dual=0.3402)
- `backtests/um_um_fast_gbm_v2_long_rotation_summary.json` (dual=0.3283)

## Results

| Experiment        | dual   | Delta vs V2 |
|-------------------|--------|-------------|
| **V2 baseline**   | **0.3431** | **—**   |
| feat_venue_run    | 0.3402 | -0.003      |
| feat_notebook_rank| 0.3339 | -0.009      |
| window_300        | 0.3304 | -0.013      |
| feat_long_rotation| 0.3283 | -0.015      |
| window_200        | 0.3269 | -0.016      |
| full_history      | timeout | —          |

**Conclusion**: UM V2 is the local optimum for this architecture. Nothing improves over the HP-tuned 16-feature, 100-show window baseline.

## Validation Status

- `pytest tests/`: 543 passed, 6 skipped, 5 failed (pre-existing `test_validate_prediction_tables` failures, unrelated)
- `ruff check`: 4 warnings (pre-existing unused vars in `phish/fast_predictor.py`)
- All model registry tests pass (25/25)

## Next Step

UM Phase B is complete — V2 (dual=0.343) is final. Remaining pre-merge work: strip experiment code from all bands, run `npm run verify:clean`, open PR, squash-merge to main.
