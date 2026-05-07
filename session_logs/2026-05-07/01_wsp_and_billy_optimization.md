# Session 01 — WSP Optimization + Billy V10 Rebase

**Date**: 2026-05-07
**Branch**: `feat/single-model-per-band`

## Goal

Optimize WSP and Billy prediction models. WSP: run full experiment pipeline from scratch (no prior WSP experiments existed). Billy: rebase to V10 baseline and test ported features from other bands.

## Constraints

- Use `uv run` for all commands
- 100-show walk-forward backtest
- Never work on `main`
- No Supabase writes — snapshot-only evaluation
- Promotion threshold: dual +0.005 for WSP; same for Billy

## Shared Infra Change

**Candidate-pruning hooks added to `PhishFastPredictor`** (`phish/fast_predictor.py`):
- Added `_candidate_recent_shows()` and `_candidate_top_career()` overridable methods
- Updated 3 call sites (`train`, `predict`, `build_diagnostic_training_frame`) to pass hook values explicitly
- Default Phish behavior unchanged (150 recent / 100 career)
- WSP overrides these hooks to use its own constants

## WSP Optimization

### Commands Run

```bash
# Baseline
uv run python scripts/run_phase_b_backtest.py --band wsp --predictor jambandnerd.models.wsp.fast_predictor.WSPFastPredictor --shows 100 --snapshot-root .snapshots/wsp

# Sweeps
uv run python scripts/run_experiment.py --band wsp --sweep candidate_sweep --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep hp_sweep --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep feature_sweep --shows 100 --snapshot-root .snapshots/wsp
uv run python scripts/run_experiment.py --band wsp --sweep combo_sweep --shows 100 --snapshot-root .snapshots/wsp

# V2 promotion backtest
uv run python scripts/run_phase_b_backtest.py --band wsp --predictor jambandnerd.models.wsp.fast_predictor.WSPFastPredictor --shows 100 --snapshot-root .snapshots/wsp --out-dir backtests
```

### Results

| Experiment | dual | p@25 | r@50 | vs V1 |
|---|---|---|---|---|
| V1 baseline | 0.4343 | 0.2824 | 0.5636 | — |
| hp_lr003_r700 | 0.4385 | 0.2788 | 0.5650 | +0.0042 |
| hp_lambda01 | 0.4374 | 0.2888 | 0.5698 | +0.0031 |
| feat_long_rotation | 0.4437 | 0.2992 | 0.5645 | +0.0094 |
| combo_lr003_long_rotation | 0.4484 | 0.2980 | 0.5678 | +0.0141 |

**Winner**: combo (long_rotation features + lr=0.03, rounds=700) → promoted to WSPFastPredictor V2.

Candidate sweep (5 variants) had zero impact — WSP's catalog is small enough that candidate bounds don't affect results.

### WSP Setlist Sizes

Median 21 songs, IQR 18-23, 67.7% >=20. K=25 is the natural product-facing K for WSP. F1@25 adopted as primary metric going forward.

### Promotion Changes

- `WSPFastPredictor` MODEL_VERSION → `wsp_fast_gbm_v2`
- 19 features: 16 V2 base + plays_past_100, diff_50_to_100, long_rotation_pressure
- HP: lr=0.03, rounds=700
- Metadata updated: dual=0.448 (+0.014 vs V1)

## Billy V10 Rebase + Experiments

### Commands Run

```bash
# Baseline
uv run python scripts/run_phase_b_backtest.py --band billy --predictor jambandnerd.models.billy.fast_predictor.BillyFastPredictorV10 --shows 100 --snapshot-root .snapshots/billy_phase_b

# Sweeps
uv run python scripts/run_experiment.py --band billy --sweep feature_sweep --shows 100 --snapshot-root .snapshots/billy_phase_b
uv run python scripts/run_experiment.py --band billy --sweep window_sweep --shows 100 --snapshot-root .snapshots/billy_phase_b
uv run python scripts/run_experiment.py --band billy --sweep hp_v10_sweep --shows 100 --snapshot-root .snapshots/billy_phase_b
```

### Results

| Experiment | dual | vs V10 |
|---|---|---|
| V10 baseline | 0.3880 | — |
| feat_plays_past_year | 0.3820 | -0.006 |
| feat_long_rotation | 0.3854 | -0.003 |
| feat_v5_features | 0.3637 | -0.024 |
| window_early_stop | 0.3752 | -0.013 |
| window_full_history | 0.3725 | -0.015 |
| window_150 | 0.3906 | +0.003 |
| hp_lr003_r500 | 0.3806 | -0.007 |
| hp_lambda01 | 0.3846 | -0.003 |
| hp_leaves7 | 0.3833 | -0.005 |
| hp_leaves31_r500 | 0.3694 | -0.019 |

**Conclusion**: V10 is the local optimum. All feature/HP/window variants underperform or produce sub-threshold gains. Billy resists the features that helped every other band (plays_past_year: -0.006, long_rotation: -0.003, notebook_rank: -0.074 from prior history).

### Billy Changes

- `_BASE_PREDICTOR_PATHS["billy"]` rebased to `BillyFastBaselinePredictor` (V10)
- 5 new experiment subclasses added: `BillyFastV10PlaysPastYear`, `BillyFastV10LongRotation`, `BillyFastV10EarlyStop`, `BillyFastV10FullHistory`, `BillyFastV10Window150`
- `_window_plays_by_days` helper added to Billy's fast_predictor module
- 3 new sweep configs: feature_sweep, window_sweep, hp_v10_sweep
- Historical V3-based sweeps preserved

## Files Changed

### WSP
- `src/jambandnerd/models/phish/fast_predictor.py` — candidate-pruning hooks (shared infra)
- `src/jambandnerd/models/wsp/fast_predictor.py` — V2 promotion + experiment subclasses
- `src/jambandnerd/models/wsp/experiments.py` — sweep configs (NEW)
- `src/jambandnerd/models/metadata.py` — WSP version bump
- `tests/models/test_wsp_model.py` — 20 tests (NEW)

### Billy
- `src/jambandnerd/models/billy/fast_predictor.py` — V10 experiment subclasses + helper
- `src/jambandnerd/models/billy/experiments.py` — feature/window/HP V10 sweeps
- `tests/models/test_billy_model.py` — 9 new test functions

### Shared
- `scripts/run_experiment.py` — WSP registered, Billy rebased to V10
- `tests/models/test_model_registry.py` — WSP version assertion updated

## Validation Status

- `pytest tests/models/test_wsp_model.py`: 20 passed
- `pytest tests/models/test_billy_model.py`: 25 passed
- `pytest tests/models/test_phish_model.py`: 18 passed
- `pytest tests/models/test_model_registry.py`: 7 passed
- **Total: 78 passed, 0 failed**
- `ruff check`: 0 issues on all modified files
- WSP V2 backtest confirmed: dual=0.448 (matches combo experiment)
- Billy V10 backtest confirmed: dual=0.388

## Artifacts

- `backtests/wsp_wsp_fast_gbm_v1_summary.json` (V1 baseline)
- `backtests/wsp_wsp_fast_gbm_v2_summary.json` (V2 promoted)
- `backtests/billy_billy_fast_gbm_v10_hp_tuned_summary.json` (V10 confirmation)
- 10 sweep result summaries in `backtests/` (5 candidate + 6 HP + 4 feature + 1 combo for WSP; 3 feature + 3 window + 4 HP for Billy)

## Band Status After This Session

| Band | Model | dual | Status |
|---|---|---|---|
| Goose | GooseFastRankPredictor | 0.409 | Promoted |
| Phish | PhishFastPlusNotebookRankVenueRun | 0.419 | Promoted |
| UM | UMFastPredictorV2 | 0.343 | Promoted |
| WSP | WSPFastPredictor V2 | 0.448 | **Promoted this session** |
| Billy | BillyFastPredictorV10 | 0.388 | Local optimum, no promotion |
| Eggy | — | — | Excluded from Phase A |

## Next Steps

1. Session log + PLAYBOOK update for Billy's feature-resistance pattern
2. Pre-merge cleanup: strip experiment code, `npm run verify:clean`, open PR to main
3. Billy architecture exploration needed — current feature+HP pattern is exhausted; new direction required (different modeling approach or Billy-specific features beyond the ported inter-band pattern)
