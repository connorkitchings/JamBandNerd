# Deal Ablation Infrastructure — Batch 1 Setup

## Goal

Add minimal infrastructure to enable Deal hyperparameter and feature-subset ablation
experiments, and define the 10 Batch 1 experiments to run against the canonical
`last_50` all-band baseline.

## Summary

- Expanded `DealPredictor.__init__` with 5 new backward-compatible parameters:
  `retired_gap_threshold`, `training_window_shows`, `min_training_shows`,
  `feature_columns`, `positive_weight_cap`.
- Updated `train()` to use instance attributes instead of module-level constants,
  and to validate feature columns against the training frame before training.
- Threaded `candidate_overrides: dict | None` through the comparison plumbing:
  `build_evaluation_predictor`, `score_model_on_target_shows`,
  `maybe_build_model_diagnostics`, `extract_experiment_metadata`.
- Added `--deal-overrides` JSON CLI argument to `compare_models.py`, with full
  resume-validation support.
- Created `scripts/analyze_ablations.py` — prints a ranked markdown comparison
  table from a batch directory of ablation JSON reports.
- Created `docs/reports/model_baselines/ablations/batch1/` output directory.

## Files Changed

- `src/jambandnerd/models/deal/model.py` — constructor + train() expansions
- `src/jambandnerd/models/comparison.py` — candidate_overrides threading
- `scripts/compare_models.py` — CLI arg + generate_report wiring
- `tests/models/test_deal_model.py` — 3 new ablation unit tests (feature subset,
  weight cap, invalid columns)
- `tests/pipeline/test_compare_models.py` — 1 new overrides metadata test;
  updated existing mock lambdas to accept `candidate_overrides` kwarg
- `scripts/analyze_ablations.py` — new analysis script (NEW)
- `docs/reports/model_baselines/ablations/batch1/.gitkeep` — output directory (NEW)

## Validation

- `uv run black --check` + `uv run ruff check` — all clean
- `uv run pytest` — 200 passed, 6 skipped

## Batch 1 Experiments (ready to run)

Each run: `uv run python scripts/compare_models.py --candidate-model deal --band all --window 50 --fresh-training --feature-set-label {LABEL} --deal-overrides '{OVERRIDES}' --output docs/reports/model_baselines/ablations/batch1/{LABEL}.json`

| Label | Overrides |
|---|---|
| `threshold_min3` | `{"min_plays_threshold": 3}` |
| `threshold_min8` | `{"min_plays_threshold": 8}` |
| `threshold_retire200` | `{"retired_gap_threshold": 200}` |
| `recency_window100` | `{"training_window_shows": 100}` |
| `recency_window50` | `{"training_window_shows": 50}` |
| `gap_only` | `{"feature_columns": ["current_gap", "avg_ltp", "recent_avg_ltp", "overdue_metric", "gap_z_score"]}` |
| `freq_only` | `{"feature_columns": ["plays_past_year", "plays_past_2yr", "pct_shows_6mo", "pct_shows_1yr", "pct_shows_all_time", "diff_6mo_to_1yr", "diff_1yr_to_alltime"]}` |
| `no_venue` | `{"feature_columns": ["current_gap", "avg_ltp", "recent_avg_ltp", "overdue_metric", "gap_z_score", "plays_past_year", "plays_past_2yr", "pct_shows_6mo", "pct_shows_1yr", "pct_shows_all_time", "diff_6mo_to_1yr", "diff_1yr_to_alltime"]}` |
| `reg_strong` | `{"regularization": 0.05, "epochs": 600}` |
| `weight_cap10` | `{"positive_weight_cap": 10.0}` |

After all 10 complete, analyze results:
```
uv run python scripts/analyze_ablations.py --batch-dir docs/reports/model_baselines/ablations/batch1
```

## Next Step

Run Batch 1 experiments (recommended order: threshold → reg/weighting → feature
subsets → recency, since runtime increases in that order). Each is independently
resumable via `--output`. After results are in, identify candidates beating the
baseline for Batch 2 combination experiments.
