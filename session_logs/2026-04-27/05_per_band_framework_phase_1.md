# Per-Band Model Framework — Phase 1

## Goal

Build the reusable scaffolding for Phase B per-band setlist prediction models
before iterating on Goose v2. The framework must:
1. Support two predictor families (logistic via `DealPredictor`, GBM via LightGBM).
2. Express a dual objective: precision@10 (head) + recall@50 (long list).
3. Provide a recorded promotion gate (not a human-only decision log).
4. Pass with 380 tests and `npm run verify:python` clean.

## Decisions Locked

- **Single ranker, dual scoring.** One ranked list per show; same scores used
  for p@10 (top 10) and r@50 (top 50). No two-stage cascade.
- **Two predictor families.** Each band's Phase B model picks the winner via
  walk-forward backtest; both return `List[DealPrediction]` and are compatible
  with the existing Deal serializer.
- **Framework first.** Scaffold is complete before Goose v2 training starts.
- **Defer dev→feat merge.** Only `audit_supabase_tables.py` is a real conflict.

## Files Created

| File | Purpose |
|---|---|
| `src/jambandnerd/models/gbm/__init__.py` | GBM module package |
| `src/jambandnerd/models/gbm/predictor.py` | `BandGbmPredictor` (native LightGBM, no sklearn) |
| `src/jambandnerd/models/gbm/serialization.py` | Delegates to Deal serializer |
| `tests/models/test_per_band_template.py` | Parametrized framework contract (15 tests) |
| `tests/models/test_dual_objective_metrics.py` | `dual_objective_score` + promotion gate (11 tests) |
| `tests/models/test_band_gbm_predictor.py` | GBM smoke: train/predict/leakage/empty (3 tests) |
| `docs/contributor/developer_guide/per_band_model_template.md` | Template guide for new bands |

## Files Modified

| File | Change |
|---|---|
| `src/jambandnerd/config/models.py` | Added `DUAL_OBJECTIVE_ALPHA` (0.5), `BAND_DUAL_OBJECTIVE_ALPHA` |
| `src/jambandnerd/models/accuracy.py` | Added `BacktestSummary`, `dual_objective_score`, `dual_objective_score_for_band` |
| `src/jambandnerd/models/readiness.py` | Added `PromotionDecision`, `is_band_promotion_eligible` |
| `scripts/run_backtest.py` | Added `DUAL OBJECTIVE` summary line after per-K metrics |
| `pyproject.toml` | Added `lightgbm>=4.0.0` dependency |
| `.agent/PLAYBOOK.md` | Captured per-band template pattern + dual-objective gate |

## Key Contracts

**`dual_objective_score(p10, r50, alpha=0.5)`** in `models/accuracy.py`: single
scalar for ranking candidates. Default α=0.5 (equal weight). Per-band override
via `BAND_DUAL_OBJECTIVE_ALPHA`.

**`is_band_promotion_eligible(candidate, incumbent, ...)`** in `models/readiness.py`:
requires Δp@10 ≥ +2pp AND Δr@50 ≥ +2pp over the same 100-show window.
Returns `PromotionDecision(eligible, blockers, ...)`.

**`BandGbmPredictor`** in `models/gbm/predictor.py`: native LightGBM LambdaRank,
same input contract as `DealPredictor`, returns `List[DealPrediction]`.
Uses `build_training_frame` + `get_candidate_features` from `deal/features.py`.

## Validation

```
npm run verify:python → 380 passed, 6 skipped
```

## Next Step

Phase 2: Goose v2 — add band-specific features (`models/goose/features.py`),
run both logistic and GBM variants on last 100 shows with `run_backtest.py
--shows 100 --dry-run`, apply promotion gate, promote the winner.
