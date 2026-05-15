# Session 04: Band-Agnostic Fast GBM Predictors for Phish, WSP, UM

## Goal
Build custom LightGBM predictors for Phish, WSP, and UM following the BillyFast V6 pattern (presence-matrix + LambdaRank + early stopping) to replace Deal v2 / Notebook baselines.

## Constraints
- Branch: `feat/three-stage-forecasting`
- `reference_date` anti-leakage rule applies
- Snapshots used for offline backtesting (no live DB hits)
- Pre-existing Phish test failures excluded from validation

## Commands Run
```bash
# PhishFast V1 baseline
uv run python scripts/run_phase_b_backtest.py --band phish --predictor jambandnerd.models.phish.fast_predictor.PhishFastPredictor --shows 100 --snapshot-root .snapshots/phish_phase_b

# PhishFast V2 (16 features + early stopping)
uv run python scripts/run_phase_b_backtest.py --band phish --predictor jambandnerd.models.phish.fast_predictor.PhishFastPredictorV2 --shows 100 --snapshot-root .snapshots/phish_phase_b

# WSPFast V1 (PhishFastV2 architecture)
uv run python scripts/run_phase_b_backtest.py --band wsp --predictor jambandnerd.models.wsp.fast_predictor.WSPFastPredictor --shows 100 --snapshot-root .snapshots/wsp

# UMFast V1 (PhishFastV2 architecture)
uv run python scripts/run_phase_b_backtest.py --band um --predictor jambandnerd.models.um.fast_predictor.UMFastPredictor --shows 100 --snapshot-root .snapshots/um_phase_b

# Tests
uv run python -m pytest tests/models/ -q -k "not test_build_gap_matrix and not test_run_position and not test_tour_position and not test_get_candidate_songs and not test_predict_without_train and not test_train_with_empty and not test_train_with_insufficient"
# 163 passed, 9 deselected (all pre-existing failures)
```

## Files Changed
- `src/jambandnerd/models/phish/fast_predictor.py` — added `_extra_training_row_features` / `_extra_predict_features` hooks to base class, integrated into train()/predict(), created `PhishFastPredictorV2` (16 features + early stopping)
- `src/jambandnerd/models/phish/__init__.py` — export PhishFastPredictorV2
- `src/jambandnerd/models/wsp/__init__.py` — new module
- `src/jambandnerd/models/wsp/fast_predictor.py` — new `WSPFastPredictor` (subclasses PhishFastPredictorV2)
- `src/jambandnerd/models/um/__init__.py` — new module
- `src/jambandnerd/models/um/fast_predictor.py` — new `UMFastPredictor` (subclasses PhishFastPredictorV2)
- `tests/models/test_model_registry.py` — updated stale Phish registry assertion
- `.agent/PLAYBOOK.md` — added band-agnostic fast predictor success pattern

## Artifacts Produced
- `backtests/phish_phish_fast_gbm_v1_summary.json` — V1: dual=0.396
- `backtests/phish_phish_fast_gbm_v2_summary.json` — V2: dual=0.405
- `backtests/wsp_wsp_fast_gbm_v1_summary.json` — WSP: dual=0.434
- `backtests/um_um_fast_gbm_v1_summary.json` — UM: dual=0.323

## Results — Updated Best Model Per Band (dual_score, 100 shows)

| Band | Best Model | dual | Previous Best | dual | Delta |
|---|---|---|---|---|---|
| phish | PhishFast V2 | **0.405** | Deal v2 | 0.391 | +0.014 |
| wsp | WSPFast V1 | **0.434** | Deal v2 | 0.408 | +0.026 |
| um | UMFast V1 | **0.323** | Deal v2 | 0.314 | +0.009 |
| billy | BillyFast V6 | **0.373** | — | — | (prior) |
| goose | Notebook 1yr | **0.408** | — | — | (prior) |

## Validation Status
- 163 model tests pass, 9 deselected (all pre-existing PhishFast test failures from before this session)
- Registry test fixed (Phish now dispatches to PhishFastPredictor, not BaselinePredictor)
- Backtests completed for all 3 new models against local snapshots
- `npm run verify:python` / `verify:docs` / `verify:web` not run (focused on model layer only)

## Next Step
Register WSPFast and UMFast in `_BAND_PREDICTOR_CLASSES` in `models/registry.py` and add `BandMetadata` entries to `models/metadata.py` to complete the per-band model promotion pipeline. Then run `promote_phase_b_winner.py` for each band to validate against the promotion gate.
