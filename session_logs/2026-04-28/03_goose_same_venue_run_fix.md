# Goose Same-Venue Run Fix

## Goal

Fix the Goose V3 same-venue-run training feature plumbing, prune diagnosed
dead/noisy features, and re-run the 50-show diagnostic plus backtest.

## Root Cause

The confirmed root cause was the candidate-filter boundary, not missing target
context, venue normalization, or merge key drift.

`compute_goose_song_features` produced non-zero
`same_venue_run_prior_play_count`, but the affected songs were removed from the
Deal-style candidate set before the Goose feature merge because they were
recently played. A representative target, `(727, 2025-05-10)`, had 24 songs with
non-zero same-run prior counts and 0 of those songs remained in candidates.

## Fix

- Added an optional candidate-builder hook to Deal `build_training_frame`, with
  the default behavior unchanged.
- Attached target show context to each walk-forward training `ModelData`.
- Added a Goose V3-only candidate helper that starts from Deal features and
  re-admits current same-venue-run songs while preserving the retired-gap
  threshold.
- Removed the temporary debug print from Goose training augmentation.

## Pruned Features

Removed from `GOOSE_EXTRA_FEATURES` and feature computation:

- `pct_shows_10`
- `pct_shows_25`
- `dow_play_rate`

## Verification

Commands run:

```bash
uv run pytest tests/models/test_goose_features.py tests/models/test_goose_model.py -q
uv run ruff check src/jambandnerd/models/deal/features.py src/jambandnerd/models/goose/ src/jambandnerd/transformations/run_context.py
uv run black --check src/jambandnerd/models/deal/features.py src/jambandnerd/models/goose/ src/jambandnerd/transformations/run_context.py
uv run python scripts/diagnose_goose_features.py --band goose --predictor jambandnerd.models.goose.model.GooseGbmTop10V3Predictor --shows 50 --snapshot-root .snapshots/goose_phase_b
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseGbmTop10V3Predictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
```

Results:

- Targeted tests: 21 passed.
- Ruff and Black checks passed.
- Diagnostic report:
  `.snapshots/goose_phase_b/diagnostics/goose_goose_phase_b_v3_gbm_top10_50shows.md`
- Diagnostic training rows: 351,182.
- Feature count: 28.
- `same_venue_run_prior_played`: zero rate 96.3%, gain 1,486, split 1.
- `same_venue_run_prior_play_share`: zero rate 96.3%, gain 19, split 1.
- `same_venue_run_prior_play_count`: zero rate 96.3%, gain 0, split 0.

## Backtest

50-show V3 backtest:

| metric | value |
| --- | ---: |
| p@10 | 0.242 |
| p@25 | 0.195 |
| r@50 | 0.528 |
| weighted_p | 0.199 |
| dual_score | 0.385 |

The prior V3 50-show dual baseline was 0.382, so the post-fix/prune run moved
slightly positive to 0.385. The same-venue prior features are now measurable,
but the positive row rate remains sparse at 3.7%, so the family still deserves
evidence-based ablation before promotion work.

## Notebook Blend Follow-Up

Added offline blend evidence tooling:

- `scripts/evaluate_goose_notebook_blend.py`
- `tests/scripts/test_evaluate_goose_notebook_blend.py`

Commands run:

```bash
uv run pytest tests/models/test_goose_model.py tests/models/test_goose_features.py tests/scripts/test_evaluate_goose_notebook_blend.py -q
uv run ruff check scripts/evaluate_goose_notebook_blend.py src/jambandnerd/models/goose/ tests/scripts/test_evaluate_goose_notebook_blend.py
uv run black --check scripts/evaluate_goose_notebook_blend.py src/jambandnerd/models/goose/ tests/scripts/test_evaluate_goose_notebook_blend.py
uv run python scripts/evaluate_goose_notebook_blend.py --band goose --base-predictor jambandnerd.models.goose.model.GooseGbmTop10V3Predictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/blends
uv run python scripts/evaluate_goose_notebook_blend.py --band goose --base-predictor jambandnerd.models.goose.model.GooseGbmV2Predictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/blends
```

Results:

| base | best alpha | p@10 | r@50 | dual | Δdual vs Notebook |
| --- | ---: | ---: | ---: | ---: | ---: |
| V3 GBM top-10 | 0.40 | 0.264 | 0.535 | 0.399 | +0.008 |
| V2 GBM | 0.60 | 0.274 | 0.545 | 0.410 | +0.019 |

Artifacts:

- `.snapshots/goose_phase_b/blends/goose_goose_phase_b_v3_gbm_top10_notebook_blend_50shows.md`
- `.snapshots/goose_phase_b/blends/goose_goose_phase_b_v2_gbm_notebook_blend_50shows.md`

The V2 GBM + Notebook rank blend clears the 50-show bar: it beats Notebook on
dual score and exceeds Notebook p@10 while preserving the GBM r@50 advantage.
Next implementation candidate should codify the V2-based rank blend rather than
continuing from fixed V3.
