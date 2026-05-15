# Goose GBM + Notebook Blend Candidate

## Goal

Continue Goose Phase B model development by codifying the V2 GBM + Notebook
rank blend that previously looked strongest in offline evidence.

## Constraints

- Keep the active Goose registry and `GoosePredictor` promotion unchanged.
- Preserve the `reference_date` anti-leakage boundary.
- Keep the model implementation Goose-owned under `src/jambandnerd/models/goose/`.
- Pair prediction behavior changes with focused tests.

## Changes

- Added `GooseGbmNotebookBlendPredictor`.
- The candidate subclasses `GooseGbmV2Predictor` and blends normalized per-show
  rank scores:
  - 60% V2 GBM rank
  - 40% Notebook rank
- Added Goose-owned helpers for Notebook-style ranking and deterministic
  rank-blended candidate ordering.
- Exported the candidate from `jambandnerd.models.goose`.
- Added unit tests for:
  - default alpha and alpha validation
  - deterministic blend ranking
  - train/predict compatibility without persisted artifacts

## Commands Run

```bash
uv run pytest tests/models/test_goose_model.py tests/models/test_goose_features.py tests/scripts/test_evaluate_goose_notebook_blend.py -q
uv run ruff check src/jambandnerd/models/goose/model.py src/jambandnerd/models/goose/__init__.py tests/models/test_goose_model.py
uv run black --check src/jambandnerd/models/goose/model.py src/jambandnerd/models/goose/__init__.py tests/models/test_goose_model.py
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseGbmNotebookBlendPredictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv run python scripts/promote_phase_b_winner.py --incumbent .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v1_summary.json --candidate .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v4_gbm_notebook_blend_summary.json --min-shows 50
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseGbmNotebookBlendPredictor --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GoosePredictor --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv run python scripts/promote_phase_b_winner.py --incumbent .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v1_summary.json --candidate .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v4_gbm_notebook_blend_summary.json --min-shows 100
uv run python scripts/evaluate_goose_notebook_blend.py --band goose --base-predictor jambandnerd.models.goose.model.GooseGbmV2Predictor --shows 100 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/blends --alpha-step 0.05
```

## Validation Status

- Targeted pytest: 29 passed.
- Ruff: passed.
- Black: passed after formatting `src/jambandnerd/models/goose/model.py`.
- 50-show snapshot backtest completed:

| metric | value |
| --- | ---: |
| p@10 | 0.274 |
| p@25 | 0.198 |
| r@50 | 0.545 |
| weighted_p | 0.207 |
| dual_score | 0.410 |

Promotion helper result against `goose_phase_b_v1`:

- Δp@10: +0.0280, clears +0.0200 threshold.
- Δr@50: +0.0191, misses +0.0200 threshold by 0.0009.
- Δdual: +0.0236.
- Candidate is **not eligible** for promotion yet.

100-show required-window validation:

| model | p@10 | p@25 | r@50 | weighted_p | dual |
| --- | ---: | ---: | ---: | ---: | ---: |
| `goose_phase_b_v1` | 0.270 | 0.212 | 0.535 | 0.216 | 0.403 |
| `goose_phase_b_v4_gbm_notebook_blend` | 0.272 | 0.215 | 0.549 | 0.220 | 0.411 |

100-show promotion helper result:

- Δp@10: +0.0020, misses +0.0200 threshold.
- Δr@50: +0.0142, misses +0.0200 threshold.
- Δdual: +0.0081.
- Candidate is **not eligible** for promotion.
- The planned 100-show alpha-sensitivity command was started but intentionally
  interrupted/paused by the user before completion; no alpha-sweep result is
  available from this session.

## Files Changed / Artifacts Produced

- `src/jambandnerd/models/goose/model.py`
- `src/jambandnerd/models/goose/__init__.py`
- `tests/models/test_goose_model.py`
- `.snapshots/goose_phase_b/backtests/goose_goose_phase_b_v4_gbm_notebook_blend_50shows.jsonl`
- `.snapshots/goose_phase_b/backtests/goose_goose_phase_b_v4_gbm_notebook_blend_summary.json`
- `.snapshots/goose_phase_b/backtests/goose_goose_phase_b_v4_gbm_notebook_blend_100shows.jsonl`
- `.snapshots/goose_phase_b/backtests/goose_goose_phase_b_v1_100shows.jsonl`
- `.snapshots/goose_phase_b/backtests/goose_goose_phase_b_v1_summary.json`

## Next Step

Resume the 100-show alpha-sensitivity sweep for `GooseGbmV2Predictor` +
Notebook before considering any further Goose promotion work. Leave registry
promotion unchanged unless a candidate clears both p@10 and r@50 thresholds on
the required 100-show window.
