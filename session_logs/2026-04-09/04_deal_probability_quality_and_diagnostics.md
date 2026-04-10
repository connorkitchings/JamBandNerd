# Deal Probability Quality And Diagnostics

## Goal

Improve Deal's internal replacement-readiness versus CK+ by strengthening
historical-only feature engineering, expanding probability-quality diagnostics,
and surfacing those diagnostics in the canonical comparison report without
promoting Deal to pipeline or web surfaces.

## Summary

- Expanded the Deal feature set with new historical-only signals focused on
  ranking separation and recency pressure:
  - `gap_vs_recent_ratio`
  - `gap_percentile`
  - `recent_gap_delta`
  - `plays_past_90d`
  - `pct_shows_90d`
  - `diff_90d_to_1yr`
  - `recent_play_share_90d`
  - `decayed_play_sum_180d`
  - `days_since_last_play`
- Extended Deal training artifacts and evaluation reports with:
  - training probability-quality summaries
  - training positive-vs-negative separation summaries
  - calibration-error summaries
  - current-candidate probability-quality summaries
- Upgraded `scripts/compare_models.py` so reports now include a compact
  `candidate_diagnostics_summary` whenever `--include-candidate-diagnostics`
  is enabled.
- Updated the Deal reference doc to describe the expanded feature/diagnostic
  surface and to reaffirm that Deal remains an internal evaluation candidate.

## Validation

- `uv run ruff check src/jambandnerd/models/deal/features.py src/jambandnerd/models/deal/model.py scripts/compare_models.py tests/models/test_deal_model.py tests/pipeline/test_compare_models.py`
- `uv run pytest tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py`

Result:
- Focused Ruff check passed.
- Focused pytest suite passed (`27 passed`).

## Notes

- A fresh-trained all-band comparison run was started with:
  `uv run python scripts/compare_models.py --candidate-model deal --band all --fresh-training --include-candidate-diagnostics --output /tmp/deal_compare_2026-04-09.json`
- The live run progressed through real-table loading and into the Eggy scoring
  loop, but it was not allowed to complete in this session because the full
  all-band fresh-training replay is materially slower than the code-validation
  pass.

## Next Step

Run the canonical all-band fresh-trained comparison to measure whether the new
Deal feature set materially improves the CK+ promotion case, then decide
whether the next tranche should focus on additional feature work or internal
shadow-run application changes.
