# Goose Backtest Results + Predictor Retirement

## Goal

Run the three-way 100-show walk-forward backtest (GoosePredictor vs
GooseGbmNotebookBlendPredictor vs GooseThreeStagePredictor) that was killed last
session due to CPU contention. Compare results and retire losers.

## Backtest Results (100 shows, sequential)

| Predictor | dual_score | dual_f1_score | weighted_score |
|---|---|---|---|
| GoosePredictor (v1) | **0.3994** | **0.2241** | **0.2132** |
| GooseGbmNotebookBlendPredictor (v4) | 0.3827 | 0.2120 | 0.2016 |
| GooseThreeStagePredictor | 0.3569 | 0.1966 | 0.1823 |

**Decision:** ThreeStage loses on every metric by a wide margin. Blend is second;
v1 baseline narrowly leads (note: prior 100-show snapshot run had blend leading v1
by ~0.01, so v1 vs blend is within noise — both are viable).

## Retirement Decision

Retired the following predictor variants (removed from codebase):
- `GooseThreeStagePredictor` — explicit loser in head-to-head
- `GooseGbmTop10V3Predictor` — exploratory variant superseded by blend
- `GooseLogisticV2Predictor` — logistic baseline superseded by GBM variants

Kept as internal base class (not public export):
- `GooseGbmV2Predictor` — still needed as base for `GooseGbmNotebookBlendPredictor`

Also removed:
- `ThreeStagePredictor` import from `goose/model.py`
- `GOOSE_TOP10_FEATURE_COLUMNS`, `GOOSE_UNUSED_DEAL_FEATURE_COLUMNS` constants
- `_goose_v3_candidate_features` helper
- `same_venue_run_show_indices` import

## Public API After Retirement

`jambandnerd.models.goose` now exports:
- `GoosePredictor` — v1 logistic baseline, best or tied for best
- `GooseGbmNotebookBlendPredictor` — GBM + Notebook rank blend, strong second
- `GOOSE_FEATURE_COLUMNS`

## Files Changed

- `src/jambandnerd/models/goose/model.py`
- `src/jambandnerd/models/goose/__init__.py`
- `tests/models/test_goose_model.py` — removed 3 tests for retired classes
- `scripts/evaluate_goose_notebook_blend.py` — default updated to `GooseGbmV2Predictor`
- `scripts/diagnose_goose_features.py` — default updated to `GooseGbmV2Predictor`

## Validation

`uv run pytest tests/models/ -q`: **113 passed** (116 − 3 retired tests, no regressions)

## Runtime Note

Each 100-show sequential backtest took ~2 hours wall time (~6 hours total). The prior
session's "~20 min" estimate was badly wrong. Future budget: ~2 hr/100 shows for Goose.

## Next Steps

- The branch `feat/three-stage-forecasting` can now be merged; the three-stage
  experiment is complete and retired.
- Consider whether `GooseGbmNotebookBlendPredictor` should be the production default
  over `GoosePredictor` (results are within noise; blend has richer signal).
