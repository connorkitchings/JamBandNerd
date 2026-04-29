# Setlist Prediction Algorithm Research & Implementation

## Goal

Research setlist prediction algorithms and implement the highest-ROI improvements for the single-model-per-band architecture, focusing on Goose as the first target band.

## Research Findings

### Algorithm Improvements (priority-ordered)

1. **Co-occurrence / song affinity features** — highest expected impact (+5-10% p@25). The current bag-of-songs approach scores each song independently, missing song-song interaction patterns.
2. **Set-position features** — data already in pipeline but unused (+3-7% p@25). `set_number`, `song_position`, `encore` columns flow through normalization but no model consumes them.
3. **Set cardinality prediction** — not yet implemented. Would directly address the K >> actual_set_size precision ceiling.
4. **Markov transition features** — medium impact, not yet implemented.
5. **GBM `rank_xendcg` objective** — easy swap, minor expected improvement.
6. **Reciprocal Rank Fusion** — not yet implemented, would replace alpha-blend.

### Accuracy Metrics Research

**Key finding**: precision@25 has a hard ceiling of `min(|actual|, 25) / 25`. For a typical 18-song Goose show, p@25 maxes at 72%. This distorts cross-show and cross-band comparisons.

**Recommendation**: Promote F1@25 as the primary metric. F1 reaches 1.0 regardless of set size, better handles the ceiling problem, and is already computed in `accuracy.py`. Keep p@25 as the user-facing metric ("60% of the board was right").

## Changes

### Sprint 1: GBM `rank_xendcg` Objective Swap
- Changed `objective` from `lambdarank` to `rank_xendcg` in `src/jambandnerd/models/gbm/predictor.py`
- Added `eval_at: [10, 25]` for K-specific NDCG monitoring

### Sprint 2: Set-Position Features (Shared)
- New module: `src/jambandnerd/transformations/set_position.py` — 6 band-agnostic features
- Integrated into `DEAL_FEATURE_COLUMNS` in `deal/features.py` — all bands inherit
- Added to `GOOSE_FEATURE_COLUMNS` in `goose/model.py`
- Features: `pct_set_1`, `pct_set_2`, `pct_encore`, `typical_position_pct`, `position_consistency`, `set_affinity`

### Sprint 3: Co-occurrence Features (Shared, Recency-Weighted)
- New module: `src/jambandnerd/transformations/cooccurrence.py` — 5 band-agnostic features
- Recency-weighted co-occurrence matrix using exponential decay on `show_index` (default half-life: 80 shows)
- Old shows contribute ~8% of weight at 200 shows back, avoiding stale pattern contamination
- Integrated into `DEAL_FEATURE_COLUMNS` in `deal/features.py` — all bands inherit
- Added to `GOOSE_FEATURE_COLUMNS` in `goose/model.py`
- Features: `avg_cooccurrence_with_recent`, `max_cooccurrence_with_recent`, `n_strong_pairs_recent`, `cooccurrence_with_last_played`, `pair_affinity_rank`

### Sprint 4: Metric Reframe (Side-by-Side Transition)
- Added `f1_10`, `f1_25`, `f1_50`, `dual_f1_score` to `BacktestSummary` in `accuracy.py`
- Added `dual_f1_objective_score()` and `dual_f1_objective_score_for_band()` to `accuracy.py`
- Updated promotion gate in `readiness.py`:
  - New checks: F1@25 must improve by ≥0.02, p@25 must not regress by >0.01
  - Legacy p@10/r@50 checks retained side-by-side during transition
- Updated `run_phase_b_backtest.py` to compute and report F1-based dual score
- Updated `promote_phase_b_winner.py` for backward-compatible summary loading
- Old dual objective (α·p@10 + (1-α)·r@50) retained; both reported during transition

## Commands Run

```bash
uv run pytest tests/transformations/test_set_position.py tests/transformations/test_cooccurrence.py tests/models/test_dual_objective_metrics.py -v
uv run pytest tests/ -q
npm run verify:python
```

## Validation Status

- `npm run verify:python`: all gates pass (black, ruff, pytest)
- 450 tests passed, 0 failures, 6 skipped
- All new modules have dedicated test coverage (29 new tests)

## Files Changed

- `src/jambandnerd/models/gbm/predictor.py` — rank_xendcg objective
- `src/jambandnerd/models/deal/features.py` — set-position + co-occurrence integration
- `src/jambandnerd/models/goose/model.py` — feature column updates
- `src/jambandnerd/models/accuracy.py` — F1 fields, dual F1 functions
- `src/jambandnerd/models/readiness.py` — F1-based promotion gate
- `scripts/run_phase_b_backtest.py` — F1 reporting
- `scripts/promote_phase_b_winner.py` — backward-compatible loading
- New: `src/jambandnerd/transformations/set_position.py`
- New: `src/jambandnerd/transformations/cooccurrence.py`
- New: `tests/transformations/test_set_position.py` (10 tests)
- New: `tests/transformations/test_cooccurrence.py` (19 tests)
- Updated: `tests/models/test_dual_objective_metrics.py` (4 new tests)

## Next Steps

1. **Backtest the new feature set** against the Goose 50-show snapshot to measure actual p@25 / F1@25 delta
2. **Set cardinality prediction** — build a regression model for predicted set size, truncate predictions
3. **Reciprocal Rank Fusion** — replace the alpha-blend in `GooseGbmNotebookBlendPredictor`
4. **Markov transition features** — first-order song-to-song transition matrix features
5. **Phase out legacy dual objective** — once F1-based metrics prove stable, remove p@10/r@50 gate
