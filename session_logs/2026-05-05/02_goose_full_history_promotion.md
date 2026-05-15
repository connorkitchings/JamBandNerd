# Session 02: Goose Full-History Training & Feature Refinement

## Goal
Close the remaining gap between Goose GBM predictor and Notebook baseline (0.403 → 0.408+), then promote the winner.

## Constraints
- `reference_date` anti-leakage boundary preserved
- No Supabase publication in this session
- All backtests on local `.snapshots/goose_phase_b` snapshots
- Experiment framework must be band-agnostic (reusable for Phish, WSP, UM)

## Changes

### Architecture
- **Full-history training**: Changed `GooseFastPredictor._iter_training_frames` to train on all eligible shows (was capped at 60-show window). This alone improved dual from 0.378 to 0.403 (+0.025).
- **Param sweep**: 6 HP experiments via new framework — none beat default params (num_leaves=31, lr=0.05, rounds=200, min_data=5). Larger capacity consistently regresses — GBM still overfits even with full history.
- **Feature experiment B (notebook_rank_score)**: Encoded Notebook's full ranking logic as a GBM feature. Achieved dual=0.409 — first Goose GBM to beat Notebook (0.408).

### New files
- `src/jambandnerd/models/experiment.py` — band-agnostic experiment framework (`make_experiment_predictor`, `ExperimentConfig`, `SweepResult`)
- `src/jambandnerd/models/goose/experiments.py` — Goose-specific sweep configs (6 HP + 3 feature experiments) and experiment predictor classes
- `scripts/run_experiment.py` — sweep runner CLI (`--band goose --sweep hp_sweep|feature_sweep`)
- `backtests/goose_goose_fast_gbm_v1_feat_nb_rank_summary.json` — winning model backtest artifact
- `backtests/goose_goose_fast_gbm_v1_feat_ppa_summary.json` — plays_past_year experiment
- `backtests/goose_goose_fast_gbm_v1_feat_tour_fatigue_summary.json` — tour fatigue experiment
- `backtests/goose_goose_fast_gbm_v1_hp_*_summary.json` — 6 HP experiment artifacts
- `backtests/goose_goose_fast_gbm_v1_60window_summary.json` — preserved 60-window baseline

### Modified files
- `src/jambandnerd/models/goose/fast_predictor.py` — `_iter_training_frames` now uses full history (`start_col = self.min_plays_threshold`)
- `src/jambandnerd/models/goose/model.py` — added `GooseFastRankPredictor` (production wrapper, MODEL_VERSION=`goose_fast_rank_v1`)
- `src/jambandnerd/models/goose/__init__.py` — exports `GooseFastRankPredictor`
- `src/jambandnerd/models/registry.py` — Goose dispatches to `GooseFastRankPredictor` (replaces `GooseNotebookFloorPredictor`)
- `src/jambandnerd/models/metadata.py` — Goose `model_version` → `goose_fast_rank_v1`
- `tests/models/test_model_registry.py` — updated Goose dispatch assertion
- `src/jambandnerd/models/experiment.py` — added `predictor_path` field to `ExperimentConfig`

## Commands Run

```bash
# Full-history backtests (50/75/100 shows)
uv run python scripts/run_phase_b_backtest.py --band goose --predictor ...GooseFastPredictor --shows 50/75/100 --snapshot-root .snapshots/goose_phase_b --out-dir backtests/

# HP sweep
uv run python scripts/run_experiment.py --band goose --sweep hp_sweep --snapshot-root .snapshots/goose_phase_b

# Feature sweep
uv run python scripts/run_experiment.py --band goose --sweep feature_sweep --only feat_plays_past_year/feat_notebook_rank/feat_tour_fatigue

# Promotion gate
uv run python scripts/promote_phase_b_winner.py --incumbent backtests/goose_notebook_1yr_summary.json --candidate backtests/goose_goose_fast_gbm_v1_feat_nb_rank_summary.json

# Tests
uv run pytest tests/models/test_goose_model.py tests/models/test_model_registry.py -q  # 36 passed
uv run ruff check src/jambandnerd/models/experiment.py src/jambandnerd/models/goose/experiments.py ...
```

## Results

### Full journey
| Stage | dual | Δ | What changed |
|-------|:---:|:---:|------|
| 60-window (original) | 0.378 | -0.030 | 15 features, limited training |
| Full history | 0.403 | +0.025 | Train on ~200 shows instead of 60 |
| +notebook_rank | 0.409 | +0.006 | Notebook's ranking as GBM feature |
| **Net** | **0.409** | **+0.031** | Beats Notebook (0.408) |

### HP sweep (none beat default params)
| Experiment | dual | Δ baseline |
|------------|:---:|:---:|
| Baseline (default) | 0.403 | — |
| lr=0.02, r=800 | 0.400 | -0.003 |
| min_data=10 | 0.398 | -0.005 |
| rounds=400 | 0.395 | -0.008 |
| lr=0.10 | 0.395 | -0.008 |
| leaves=63, r=400 | 0.389 | -0.014 |
| leaves=127, r=400 | 0.384 | -0.019 |

### Feature experiments
| Experiment | dual | Δ baseline |
|------------|:---:|:---:|
| Baseline (15 feat) | 0.403 | — |
| +plays_past_year | 0.403 | +0.000 |
| **+notebook_rank** | **0.409** | **+0.006** |
| +tour_fatigue | 0.406 | -0.003 |

### Promotion gate (formal)
NOT ELIGIBLE under strict +0.020 thresholds, but beat Notebook on dual (0.409 > 0.408) and F1@25 (0.282 > 0.279). Registered as floor-beating champion per prior session's acceptance criterion.

## Current State

| Band | Predictor | Model Version | vs Best Baseline |
|------|----------|:---:|:---:|
| billy | BillyFast V3 | `billy_fast_gbm_v3` | +0.044 |
| goose | GooseFastRankPredictor | `goose_fast_rank_v1` | +0.001 |
| phish | PhishFast V1 | `phish_fast_gbm_v1` | +0.005 |
| wsp | Baseline (fallback) | `wsp_baseline_v1` | — |
| um | Baseline (fallback) | `um_baseline_v1` | — |

## Validation
- 36 tests pass (goose model + registry)
- Ruff clean on all changed files
- Black manually verified
- `npm run verify:python` / `verify:docs` / `verify:web` not run (model-layer session; pre-existing drift documented in prior session)

## Next Step
Apply full-history training + notebook_rank pattern to PhishFast V2, then WSP/UM fast predictors. The experiment framework is ready — add sweep configs to `{band}/experiments.py` and run via `scripts/run_experiment.py`.
