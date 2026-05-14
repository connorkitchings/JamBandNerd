# Three-Stage Forecasting Closeout

## Goal

- Close out and commit the current `feat/three-stage-forecasting` worktree state:
  a first-pass three-stage forecasting path with calibrated GBM scores,
  transition-aware sequence optimization, and nDCG metric reporting.

## Constraints

- Preserve the current branch state without reverting unrelated work.
- Keep the new three-stage code offline/model-side only in this commit.
- Validate before committing.

## Commands Run

```bash
sed -n '1,240p' .agent/skills/end-session/SKILL.md
git status --short --branch
git diff --stat
uv run pytest tests/models/test_beam_search.py tests/models/test_calibration.py tests/models/test_ndcg.py tests/transformations/test_transitions.py tests/models/test_dual_objective_metrics.py tests/pipeline/test_compare_models.py -q
uv run ruff check src tests scripts
uv run black --check src tests scripts
npm run verify:python
```

## Files Changed Or Artifacts Produced

- Added `src/jambandnerd/models/beam_search.py` for Stage 3 sequence-aware
  ranking.
- Added `src/jambandnerd/models/calibration.py` with a small Platt scaler for
  raw GBM score calibration.
- Added `src/jambandnerd/models/three_stage/` with `ThreeStagePredictor`.
- Added `src/jambandnerd/transformations/transitions.py` for directional
  within-set bigram transition probabilities.
- Extended accuracy summaries with nDCG values.
- Updated GBM training to fit an optional calibration split.
- Added tests for beam search, calibration, nDCG, and transition matrices.
- Added `duckdb` to Python dependencies.

## Validation Status

- Targeted pytest: 52 passed.
- `uv run ruff check src tests scripts`: passed.
- `uv run black --check src tests scripts`: passed.
- `npm run verify:python`: 484 passed, 6 skipped.

## Next Step

- Run offline backtests for `ThreeStagePredictor` against Notebook and current
  GBM baselines before considering registry exposure or production wiring.
