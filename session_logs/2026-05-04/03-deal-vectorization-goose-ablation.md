# Session 03 — Deal Pipeline Vectorization + Goose Feature Ablation

## Goal
Make the Deal model feasible for all bands via pipeline vectorization, then begin systematic Goose feature engineering to beat Notebook 1yr's 0.408 dual score.

## Constraints
- Branch: `feat/three-stage-forecasting`
- All features must respect `reference_date` anti-leakage rule
- Never work on `main`
- User has ~5 hours available

## Commands Run
```bash
# Vectorization profiling
uv run python -c "... profile build_cooccurrence_matrix ..."
uv run python -c "... profile compute_set_position_features ..."
uv run python -c "... profile build_training_frame ..."
uv run python -c "... profile generate_deal_features ..."

# Tests
uv run python -m pytest tests/ -k "cooccurrence or set_position or deal" -q

# Deal backtests (5 bands, parallel)
for band in goose billy phish um wsp; do
  uv run python scripts/run_phase_b_backtest.py --band $band --predictor jambandnerd.models.deal.model.DealPredictor --shows 100 --snapshot-root .snapshots/... --out-dir backtests/
done

# Goose feature ablation (13 variants)
uv run python scripts/run_goose_ablation.py
```

## Files Changed or Produced

### Modified
- `src/jambandnerd/transformations/cooccurrence.py` — Vectorized `build_cooccurrence_matrix` (numpy matrix multiply), vectorized `compute_cooccurrence_features` (numpy array ops instead of per-song Python loop)
- `src/jambandnerd/transformations/set_position.py` — Vectorized `compute_set_position_features` (pandas groupby instead of per-song iterrows loop)
- `src/jambandnerd/models/deal/features.py` — Vectorized per-song loop in `generate_deal_features` (pre-computed groupby masks for date-range features, venue/state counts via pre-computed MultiIndex series)

### New
- `src/jambandnerd/models/goose/ablation.py` — `GooseFastAblationPredictor`: parameterized feature list, extends `GooseFastPredictor` with `plays_past_year` calendar feature
- `scripts/run_goose_ablation.py` — Batch runner for 10 ablation variants
- `backtests/goose_feature_ablation_results.json` — Ablation results JSON
- `backtests/{goose,billy,phish,um,wsp}_deal_v2_summary.json` — Deal v2 backtest summaries
- `backtests/{goose,billy,phish,um,wsp}_deal_v2_100shows.jsonl` — Per-show metrics

## Performance Improvements (Billy benchmark, 1612 songs, 1062 shows)

| Component | Before | After | Speedup |
|---|---|---|---|
| `build_cooccurrence_matrix` | minutes (O(n²×shows) Python) | 20ms (numpy matmul) | ~1000x |
| `compute_set_position_features` | 1.1s (iterrows) | 0.03s (groupby) | 37x |
| `compute_cooccurrence_features` | 0.6s (dict + per-song loop) | 0.025s (numpy array ops) | 24x |
| `generate_deal_features` | 2.3s | 0.21s | 11x |
| `build_training_frame` | >300s (timeout) | 14.4s | >21x |

## Validation Status
- 48/48 tests pass for changed modules (cooccurrence, set_position, deal)
- 525/531 full suite pass (6 pre-existing Phish model test failures)
- All Deal backtests completed successfully (5/5 bands, 100 shows each)
- Goose feature ablation completed (13 variants)

## Key Results

### Deal v2 Backtests (100 shows, dual_score)
| Band | Deal v2 | Notebook 1yr | Best |
|---|---|---|---|
| goose | 0.396 | 0.408 | Notebook |
| billy | 0.333 | 0.333 | Tie (BillyFast GBM v6 wins at 0.373) |
| phish | 0.391 | 0.390 | Deal (marginal) |
| wsp | 0.408 | 0.399 | Deal |
| um | 0.314 | 0.314 | Tie |

### Goose Feature Ablation (best results)
| Variant | # Feat | dual | Notes |
|---|---|---|---|
| core+tour+month+plays25 | 9 | 0.381 | Best GBM variant |
| +tour (individual) | 6 | 0.381 | Tour context strongest signal |
| core (baseline) | 4 | 0.372 | current_gap, plays_past_year, plays_past_50, career_play_pct |
| Notebook 1yr | 2 | 0.408 | Target to beat |
| GooseFast v1 | 15 | 0.378 | Current best GBM |

### Key Insight
The GBM cannot beat Notebook for Goose regardless of feature set. The 0.027 gap (0.381 vs 0.408) is architectural, not feature-based. Goose's small dataset (~60 training shows) causes GBM overfitting. The logistic model (0.399) confirms simpler architectures resist overfitting better.

## Next Step
Goose architecture reconsideration: test logistic regression with the 9-feature ablation set, GBM with aggressive early stopping (fewer leaves), or a Notebook+GBM rank blend. The target is beating 0.408 (Notebook 1yr). If logistic regression with minimal features approaches 0.399 (the 26-feature logistic baseline), the 9-feature set should match or exceed it.
