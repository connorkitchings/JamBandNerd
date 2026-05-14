# Billy Strings — BillyFastPredictor LightGBM Upgrade

## Goal

Improve BillyFastPredictor (standalone vectorized predictor, logistic regression baseline
dual_score=0.309) by replacing logistic regression with LightGBM LambdaRank.

## Constraints

- No cooccurrence matrix (O(n_songs² × n_shows) Python triple loop, unusable for Billy's
  scale even after presence-matrix rewrite of augment_training_frame)
- All features must be computable from the presence matrix alone (no DealPredictor inheritance)

## What Was Tried

### v2 logistic — added collinear features (did not help)
Added `avg_gap`, `overdue_metric`, `diff_25_to_50` to the v1 7-feature logistic model.
Result: **dual_score=0.300** (regression from 0.309). Features were algebraically
derivable from existing inputs — added noise, not signal.

### GBM v1 — swap logistic → LightGBM, revert to v1 7-feature set
Replaced `sklearn.LogisticRegression` with `lgb.train(objective="rank_xendcg")`.
Same 7 features as logistic v1: `gap_shows`, `plays_past_10/25/50`, `career_play_pct`,
`month_play_rate`, `is_cover`.
Result: **dual_score=0.366** (+18.4% over logistic v1).

## Files Changed

- `src/jambandnerd/models/billy/fast_predictor.py` — rewrote to use LightGBM LambdaRank
  (`_LGB_PARAMS`, `_LGB_ROUNDS=200`); reverted to 7-feature v1 set; added `self.band`
  attribute to satisfy per-band template test; `MODEL_VERSION = "billy_fast_gbm_v1"`
- `src/jambandnerd/models/metadata.py` — model_version updated to `"billy_fast_gbm_v1"`
- `tests/models/test_billy_model.py` — MODEL_VERSION assertion updated to `"billy_fast_gbm_v1"`

## Commands Run

```bash
# v2 logistic backtest (failed to improve)
time uv run python scripts/run_phase_b_backtest.py \
    --band billy --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictor \
    --shows 100 --snapshot-root .snapshots/billy_phase_b --out-dir backtests/
# → dual_score=0.300 (regression)

# GBM v1 backtest
time uv run python scripts/run_phase_b_backtest.py \
    --band billy --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictor \
    --shows 100 --snapshot-root .snapshots/billy_phase_b --out-dir backtests/
# → dual_score=0.366 (+18.4%)

uv run pytest tests/models/ -q  # 121 passed
```

## Validation

- `uv run pytest tests/models/ -q`: **121 passed, 0 failed**

## Backtest Results Summary

| Model | dual_score | p@10 | r@50 | hit@10 |
|---|---|---|---|---|
| Logistic v1 (baseline) | 0.309 | — | — | — |
| Logistic v2 (collinear features) | 0.300 | 0.214 | 0.386 | 0.790 |
| **GBM v1 (LightGBM, 7 features)** | **0.366** | **0.308** | **0.425** | **0.870** |

## Next Step

Add venue/run context features (`show_position_in_run`, `tour_position`,
`same_venue_run_*`) to the GBM — same features that helped Goose, computable from
show_date + venue info without cooccurrence. Expected to push dual_score toward 0.38+.
