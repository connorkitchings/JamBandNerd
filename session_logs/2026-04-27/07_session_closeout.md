# Session Closeout — Per-Band Framework + Goose v2

## Goal

Formally close out the session that built the Phase B per-band model
framework (log 05) and Goose v2 feature/predictor scaffolding (log 06).

## Constraints

- All changes uncommitted on `feat/single-model-per-band`
- Backtests not yet run (~3.5h each, Connor runs locally)
- No docs updated beyond `PLAYBOOK.md` and new template guide

## Commands Run

- `npm run verify:python` → 403 passed, 6 skipped (session 06)

## Files Changed / Artifacts Produced

See session logs 05 and 06 for full file lists.

### Modified (uncommitted)

| File | Change |
|---|---|
| `.agent/PLAYBOOK.md` | Per-band template pattern + dual-objective gate lessons |
| `pyproject.toml` | Added `lightgbm>=4.0.0` dependency |
| `scripts/run_backtest.py` | Dual objective summary line |
| `src/jambandnerd/config/models.py` | `DUAL_OBJECTIVE_ALPHA`, `BAND_DUAL_OBJECTIVE_ALPHA` |
| `src/jambandnerd/models/accuracy.py` | `BacktestSummary`, `dual_objective_score`, `dual_objective_score_for_band` |
| `src/jambandnerd/models/deal/model.py` | `_build_training_frame` and `_get_candidate_features` subclass hooks |
| `src/jambandnerd/models/goose/model.py` | `GooseLogisticV2Predictor`, `GooseGbmV2Predictor` |
| `src/jambandnerd/models/readiness.py` | `PromotionDecision`, `is_band_promotion_eligible` gate |
| `src/jambandnerd/transformations/gaps.py` | Carry `set_number`, `song_position`, `encore` through `historical_plays` |
| `uv.lock` | LightGBM + scipy lockfile entries |

### New (untracked)

| File | Purpose |
|---|---|
| `src/jambandnerd/models/gbm/__init__.py` | GBM module package |
| `src/jambandnerd/models/gbm/predictor.py` | `BandGbmPredictor` (native LightGBM LambdaRank) |
| `src/jambandnerd/models/gbm/serialization.py` | Delegates to Deal serializer |
| `src/jambandnerd/models/goose/features.py` | Goose Tier A + Tier B feature engineering |
| `scripts/run_phase_b_backtest.py` | Single-variant backtest → BacktestSummary JSON |
| `scripts/promote_phase_b_winner.py` | Load summaries, apply gate, print decision |
| `tests/models/test_band_gbm_predictor.py` | GBM smoke tests |
| `tests/models/test_dual_objective_metrics.py` | Dual-objective + promotion gate tests |
| `tests/models/test_goose_features.py` | Goose feature leakage + computation tests |
| `tests/models/test_per_band_template.py` | Parametrized framework contract tests |
| `tests/pipeline/test_historical_plays_set_columns.py` | Set column plumbing verification |
| `docs/contributor/developer_guide/per_band_model_template.md` | Template guide for new bands |
| `session_logs/2026-04-27/05_per_band_framework_phase_1.md` | Session log 05 |
| `session_logs/2026-04-27/06_goose_v2_framework.md` | Session log 06 |

## Validation Status

| Check | Status |
|---|---|
| `npm run verify:python` | PASSED (403 passed, 6 skipped) |
| `npm run verify:docs` | NOT RUN |
| `npm run verify:web` | NOT RUN |
| `npm run verify:clean` | NOT RUN |

## Next Step

1. Commit all changes to `feat/single-model-per-band`
2. Run three backtests locally (baseline, logistic v2, GBM v2) via `scripts/run_phase_b_backtest.py`
3. Apply promotion gate with `scripts/promote_phase_b_winner.py`
4. Promote winner and update `metadata.py` + `registry.py`
