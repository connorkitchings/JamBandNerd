# Billy Strings Tuning Experiments — V4 (HP) and V5 (Features)

## Goal

Push BillyFastPredictorV3 (dual_score=0.377, p@10=0.322, r@50=0.432) toward
user targets of p@10≥0.40 and r@50≥0.50 by trying HP tuning (V4) and feature
engineering (V5).

## Constraints

- Must beat V3 on dual_score OR p@10 to promote
- V3 uses 16 features, 200 rounds, 31 leaves
- 75-show training window, ~100–200 eligible songs per show

## Commands Run

```bash
# V4 backtest
uv run python scripts/run_phase_b_backtest.py \
  --band billy --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictorV4 \
  --shows 100 --snapshot-root .snapshots/billy_phase_b --out-dir backtests/

# V5 backtest
uv run python scripts/run_phase_b_backtest.py \
  --band billy --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictorV5 \
  --shows 100 --snapshot-root .snapshots/billy_phase_b --out-dir backtests/

uv run pytest tests/models/test_billy_model.py -q  # 22 passed
```

## Files Changed

- `src/jambandnerd/models/billy/fast_predictor.py`:
  - Added `BillyFastPredictorV4` — HP tuning (num_leaves=63, rounds=400, reg_lambda=0.1)
  - Added `BillyFastPredictorV5` — 9 new features: gap_percentile, shows_since_debut,
    is_recent_debut, gap_days, avg_days_between_plays, days_overdue, pct_set_1,
    pct_encore, set_affinity (25 features total)
  - Added `_precompute_gap_distributions`, `_precompute_first_play_col`,
    `_precompute_avg_days_between_plays` helpers
  - Updated `_prepare()` to compute and cache gap_dist, first_play_col, avg_days_bp, set_feats
  - Updated `_clean_plays()` to preserve set_number, song_position, encore columns
  - Added `BILLY_FAST_V5_FEATURE_COLS`, `_EMPTY_ARR`
  - Added import for `compute_set_position_features`
- `src/jambandnerd/models/registry.py`: V3 remains default (reverted from V4 and V5)
- `tests/models/test_billy_model.py`: Added V4 and V5 tests (22 tests total)
- `backtests/`: V4 and V5 summary + per-show jsonl files

## Backtest Results (100 shows, 2025-02-14 – 2026-04-18)

| Model | dual_score | p@10 | r@50 |
|---|---|---|---|
| V3 (production) | 0.377 | 0.322 | 0.432 |
| V4 (HP tuning — rejected) | 0.356 | 0.305 | 0.406 |
| V5 (features — rejected) | 0.364 | 0.303 | 0.424 |

Both experiments regressed across all metrics. V3 remains production default.

## Validation

- 22/22 tests pass
- Ruff + Black clean on all modified files
- Both V4 and V5 committed with backtest artifacts, registry reverted to V3

## Key Finding

Both adding complexity (V4: HP, V5: features) hurt generalization. V3's 16-feature
set with 200 rounds/31 leaves is at or past the capacity ceiling for the available
training signal (~75 shows, ~150 eligible songs per show). The model is already
extracting most of the signal the current architecture can support.

## Next Step

Try a new architecture + early stopping. Specifically:
1. Early stopping with a per-show validation holdout (find optimal round count dynamically)
2. New architecture — e.g., two-stage (coarser eligibility filter → fine-grained ranker),
   or ensemble of the presence-matrix ranker with a simpler frequency model
