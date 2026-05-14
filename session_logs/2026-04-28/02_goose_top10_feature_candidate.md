# Goose Top-10 Feature Candidate

## Goal

Implement an exploratory Goose GBM candidate focused on top-10 prediction quality
using existing internal show/setlist data only.

## Constraints

- Stay internal-data-only: no notes parsing, external venue metadata, Fantasy Goose,
  or fan-signal data.
- Keep same-venue-run behavior as a model feature, not a hard candidate filter.
- Do not register or promote the exploratory candidate unless evidence clears the
  gate.
- Preserve the `reference_date` anti-leakage boundary.

## Changes

- Added optional `ModelData.target_show_context` and plumbed target show context
  through live predictions, retained backtests, and Phase B backtests.
- Added shared same-venue-run helpers in `transformations/run_context.py`.
- Updated Goose-specific features to remove slot/role set-position features and add:
  - short-window heat features
  - unused Deal frequency features in the candidate column set
  - same-venue-run negative features
- Added exploratory `GooseGbmTop10V3Predictor`.
- Left active `GoosePredictor`, model registry, and metadata unchanged.

## Commands Run

```bash
uv run pytest tests/models/test_goose_features.py tests/models/test_goose_model.py tests/pipeline/test_prediction_reference_date_semantics.py -q
uv run ruff check src/jambandnerd/transformations/gaps.py src/jambandnerd/transformations/run_context.py src/jambandnerd/models/goose scripts/run_backtest.py scripts/run_phase_b_backtest.py scripts/generate_live_predictions.py tests/models/test_goose_features.py tests/models/test_goose_model.py tests/pipeline/test_prediction_reference_date_semantics.py
uv run black --check src/jambandnerd/transformations/gaps.py src/jambandnerd/transformations/run_context.py src/jambandnerd/models/goose scripts/run_backtest.py scripts/run_phase_b_backtest.py scripts/generate_live_predictions.py tests/models/test_goose_features.py tests/models/test_goose_model.py tests/pipeline/test_prediction_reference_date_semantics.py
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GoosePredictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseGbmTop10V3Predictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv run python scripts/promote_phase_b_winner.py --incumbent .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v1_summary.json --candidate .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v3_gbm_top10_summary.json --min-shows 50
npm run verify:python
npm run verify:docs
```

## Files Changed / Artifacts Produced

- `src/jambandnerd/transformations/gaps.py` and
  `src/jambandnerd/transformations/run_context.py`: target-context plumbing and
  same-venue-run helpers.
- `scripts/generate_live_predictions.py`, `scripts/run_backtest.py`, and
  `scripts/run_phase_b_backtest.py`: pass target show context into model data.
- `src/jambandnerd/models/goose/features.py` and
  `src/jambandnerd/models/goose/model.py`: top-10 candidate features and
  exploratory GBM predictor.
- Tests updated under `tests/models/` and
  `tests/pipeline/test_prediction_reference_date_semantics.py`.
- Local ignored evidence:
  - `.snapshots/goose_phase_b/backtests/goose_goose_phase_b_v3_gbm_top10_50shows.jsonl`
  - `.snapshots/goose_phase_b/backtests/goose_goose_phase_b_v3_gbm_top10_summary.json`

## Results

| Model | p@10 | p@25 | r@50 | dual | Gate |
|---|---:|---:|---:|---:|---|
| `goose_phase_b_v1` | 0.246 | 0.198 | 0.526 | 0.386 | incumbent |
| `goose_phase_b_v3_gbm_top10` | 0.248 | 0.184 | 0.516 | 0.382 | not eligible |

Promotion blockers:

- `p10_delta_below_threshold:0.0020<0.02`
- `r50_delta_below_threshold:-0.0101<0.02`

## Metric Decisions

- Use `p@10` as the primary candidate optimization target.
- Use `r@50` as the secondary broad-coverage objective.
- Treat top-25 as a bridge/guardrail instead of an equal primary objective.
  Preferred top-25 readout is `avg_matches@25`/`p@25`; a candidate should not
  buy a tiny top-10 lift by losing meaningful main-board quality.
- For future single-score experiment ranking, consider:
  `0.45 * p@10 + 0.30 * F1@25 + 0.25 * r@50`, but keep component metrics
  visible so regressions are not hidden.

## Modeling Findings

- The current framework can run walk-forward comparisons and promotion checks,
  but it does not yet provide strong feature-selection evidence.
- Before inventing more Goose-specific features, add a feature diagnostics layer
  that reports descriptives, missing/zero rates, positive-rate lift by decile,
  feature correlation, GBM gain/split/permutation importance, and grouped
  ablations.
- Candidate decisions should become evidence-based:
  keep feature families that improve `p@10` without materially hurting
  `avg_matches@25`/`p@25` or `r@50`; drop feature families with flat univariate
  lift, near-zero importance, or no repeatable ablation gain.

## Validation Status

- Targeted pytest, ruff, and black checks passed.
- 50-show incumbent and candidate snapshot backtests completed.
- Promotion gate correctly failed the candidate.
- `npm run verify:python` passed: 410 passed, 6 skipped.
- `npm run verify:docs` passed.

## Next Step

Do not promote or run the 100-show gate for this candidate. Build a Goose
feature diagnostics/selection workflow before adding more feature ideas.
