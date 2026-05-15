# Session 03: Phish Experiment Framework — Interrupted Wrap

## Goal
Implement the planned Phish experiment loop using `PhishFastPredictorV2` as the
incumbent, then run snapshot sweeps to identify whether a challenger beats V2
under the pragmatic gate.

## Constraints
- User redirected the session to `end-session` before further implementation.
- Do not promote Phish in `registry.py` or `metadata.py` during this session.
- No Supabase writes.
- Preserve `reference_date` anti-leakage behavior.
- No commit made during wrap-up because the user interrupted implementation and
  asked to end the session.

## Files Changed or Artifacts Produced
- `src/jambandnerd/models/phish/experiments.py`
  - Added Phish HP and feature sweeps.
  - Feature candidates include `plays_past_year`, `notebook_rank_score`,
    longer-window rotation features, and same-venue run features.
- `scripts/run_experiment.py`
  - Added Phish base predictor path, pointing HP sweeps at
    `PhishFastPredictorV2`.
- `tests/models/test_phish_model.py`
  - Fixed stale helper expectations around dense matrix column semantics.
  - Updated `ModelData` test construction.
  - Added Phish V2 and sweep-discovery coverage.
- Backtest summaries and JSONL artifacts:
  - `backtests/phish_phish_fast_gbm_v2_hp_minleaf10_summary.json`
  - `backtests/phish_phish_fast_gbm_v2_hp_minleaf20_summary.json`
  - `backtests/phish_phish_fast_gbm_v2_hp_leaves15_summary.json`
  - `backtests/phish_phish_fast_gbm_v2_hp_lr003_r700_summary.json`
  - `backtests/phish_phish_fast_gbm_v2_feat_plays_past_year_summary.json`
  - `backtests/phish_phish_fast_gbm_v2_feat_notebook_rank_summary.json`

## Commands Run
```bash
uv run pytest tests/models/test_phish_model.py -q
uv run ruff check --fix src/jambandnerd/models/phish/experiments.py scripts/run_experiment.py tests/models/test_phish_model.py
uv run ruff check src/jambandnerd/models/phish/experiments.py scripts/run_experiment.py tests/models/test_phish_model.py
uv run python scripts/run_experiment.py --band phish --sweep hp_sweep --snapshot-root .snapshots/phish_phase_b
uv run python scripts/run_experiment.py --band phish --sweep feature_sweep --snapshot-root .snapshots/phish_phase_b
```

## Validation Status
- `uv run pytest tests/models/test_phish_model.py -q` -> 18 passed.
- `uv run ruff check ...` -> passed.
- HP sweep completed all four candidates.
- Feature sweep was interrupted before the full sweep table returned. Produced
  summaries confirm `feat_plays_past_year` and `feat_notebook_rank` completed.
  `feat_long_rotation` and `feat_venue_run` were not completed.
- Process-list inspection was attempted after interruption but blocked by local
  sandbox permissions. The Codex exec session was closed.

## Results So Far
Incumbent baseline:

| Model | dual | p@10 | p@25 | r@50 | F1@25 |
| --- | ---: | ---: | ---: | ---: | ---: |
| PhishFast V2 | 0.4048 | 0.2798 | 0.2380 | 0.5297 | 0.2747 |

Completed challengers:

| Experiment | dual | p@10 | p@25 | r@50 | F1@25 |
| --- | ---: | ---: | ---: | ---: | ---: |
| hp_minleaf10 | 0.4072 | 0.2798 | 0.2440 | 0.5346 | 0.2816 |
| hp_minleaf20 | 0.4069 | 0.2737 | 0.2424 | 0.5400 | 0.2800 |
| hp_leaves15 | 0.4103 | 0.2788 | 0.2396 | 0.5418 | 0.2764 |
| hp_lr003_r700 | 0.4017 | 0.2707 | 0.2360 | 0.5328 | 0.2721 |
| feat_plays_past_year | 0.4128 | 0.2808 | 0.2372 | 0.5448 | 0.2737 |
| feat_notebook_rank | 0.4151 | 0.2838 | 0.2436 | 0.5464 | 0.2809 |

Current best completed candidate is `phish_fast_gbm_v2_feat_notebook_rank`.
It clears the pragmatic gate versus V2 and legacy baselines on the available
metrics, with no p@25 regression versus V2.

## Next Step
Decide whether to preserve or revert the partial implementation. If preserving,
finish the interrupted `feature_sweep` for `feat_long_rotation` and
`feat_venue_run`, then either promote `feat_notebook_rank` in a separate session
or document why V2 remains the candidate.
