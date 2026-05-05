# Session 04: Phish Experiment Sweep Complete + Promotion

## Goal
Complete the interrupted Phish feature sweep from session 03, run a stacked
challenger combining the two best features, and promote the winner.

## Constraints
- No Supabase writes.
- Preserve `reference_date` anti-leakage behavior.

## Files Changed
- `src/jambandnerd/models/phish/experiments.py`
  - Fixed `PhishFastPlusVenueRun._venue_run_features`: removed `or {}` guard
    that forced `bool()` on a `pd.Series`, causing "truth value is ambiguous"
    errors on every backtest show.
  - Added `PhishFastPlusNotebookRankVenueRun`: stacks notebook_rank + venue_run
    features on top of `PhishFastPlusNotebookRank`.
  - Added `feat_notebook_rank_venue_run` to `PHISH_FEATURE_SWEEP`.
- `src/jambandnerd/models/registry.py`
  - Replaced `PhishFastPredictor` with `PhishFastPlusNotebookRankVenueRun` in
    `_BAND_PREDICTOR_CLASSES["phish"]`.
  - Updated import to `from .experiments import PhishFastPlusNotebookRankVenueRun`.
- `src/jambandnerd/models/metadata.py`
  - Updated `BAND_METADATA` phish entry:
    `model_version="phish_fast_gbm_v2_feat_notebook_rank_venue_run"`.
- `src/jambandnerd/models/phish/__init__.py`
  - Added `PhishFastPlusNotebookRankVenueRun` to exports.
- `tests/models/test_phish_model.py` — updated coverage (from session 03).
- `scripts/run_experiment.py` — added Phish base predictor path (from session 03).

## Commands Run
```bash
uv run python scripts/run_experiment.py --band phish --sweep feature_sweep --only feat_venue_run --snapshot-root .snapshots/phish_phase_b
uv run python scripts/run_experiment.py --band phish --sweep feature_sweep --only feat_notebook_rank_venue_run --snapshot-root .snapshots/phish_phase_b
uv run ruff check --fix <files> && uv run ruff format <files>
uv run pytest tests/models/ -q
```

## Validation Status
- `uv run pytest tests/models/ -q` -> 178 passed.
- `uv run ruff check` -> All checks passed.
- All 9 experiments completed (V2 baseline + 4 HP + 4 feature + 1 stacked).

## Full Sweep Results

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 | delta_dual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 baseline | 0.4048 | 0.2798 | 0.2380 | 0.5297 | 0.2747 | — |
| hp_minleaf10 | 0.4072 | 0.2798 | 0.2440 | 0.5346 | 0.2816 | +0.0024 |
| hp_minleaf20 | 0.4069 | 0.2737 | 0.2424 | 0.5400 | 0.2800 | +0.0021 |
| hp_leaves15 | 0.4103 | 0.2788 | 0.2396 | 0.5418 | 0.2764 | +0.0055 |
| hp_lr003_r700 | 0.4017 | 0.2707 | 0.2360 | 0.5328 | 0.2721 | -0.0031 |
| feat_plays_past_year | 0.4128 | 0.2808 | 0.2372 | 0.5448 | 0.2737 | +0.0080 |
| feat_notebook_rank | 0.4151 | 0.2838 | 0.2436 | 0.5464 | 0.2809 | +0.0103 |
| feat_long_rotation | 0.4028 | 0.2606 | 0.2400 | 0.5449 | 0.2770 | -0.0020 |
| feat_venue_run | 0.4112 | 0.2818 | 0.2473 | 0.5406 | 0.2857 | +0.0064 |
| **feat_notebook_rank_venue_run** | **0.4186** | **0.2929** | 0.2453 | 0.5442 | 0.2831 | **+0.0138** |

## Commits
- `0502fb9` — Add Phish experiment framework: HP + feature sweeps against PhishFast V2
- `525220e` — Promote PhishFastPlusNotebookRankVenueRun as active Phish predictor

## Next Step
Run the full pipeline for Phish to generate live predictions with the promoted
model: `uv run python scripts/run_optimized_pipeline.py --band phish`.
