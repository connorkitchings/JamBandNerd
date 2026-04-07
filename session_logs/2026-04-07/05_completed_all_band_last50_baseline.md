# Completed All-Band `last_50` Baseline

## Goal

Finish the resumable all-band `last_50` Deal baseline artifact and close the
live validation loop against the existing backtest path.

## Constraints

- `last_50` is the only active comparison window.
- The comparison workflow must remain the canonical path; no ad hoc Deal-only
  runner was introduced.
- The all-band baseline had to tolerate long fresh-trained Deal runs without
  losing completed-band progress.

## Summary

- Resumed `docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json`
  from its partial checkpoint and carried it through all six active bands.
- Confirmed the final artifact is marked `report_status=complete` and lists all
  requested bands in `completed_bands`.
- Ran a live Goose Notebook backtest for `--shows 50` and confirmed the printed
  aggregate metrics match the Goose Notebook slice in the comparison artifacts
  at the same rounded values.

## Commands Run

- `./.venv/bin/black --check scripts/compare_models.py scripts/audit_shared_model_inputs.py tests/pipeline/test_compare_models.py tests/pipeline/test_audit_shared_model_inputs.py`
- `uv run ruff check scripts/compare_models.py scripts/audit_shared_model_inputs.py tests/pipeline/test_compare_models.py tests/pipeline/test_audit_shared_model_inputs.py`
- `uv run pytest tests/pipeline/test_compare_models.py tests/pipeline/test_audit_shared_model_inputs.py tests/pipeline/test_evaluate_deal_model.py -q`
- `uv run python scripts/compare_models.py --candidate-model deal --band goose --window 50 --fresh-training --output docs/reports/model_baselines/2026-04-07_deal_baseline_goose_last50.json`
- `uv run python scripts/audit_shared_model_inputs.py --band all --output docs/reports/model_baselines/2026-04-07_shared_model_input_audit.json`
- `uv run python scripts/compare_models.py --candidate-model deal --band all --window 50 --fresh-training --output docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json`
- `uv run python scripts/run_backtest.py --band goose --model notebook --shows 50`

## Files / Artifacts

- Comparison workflow and resume support:
  `scripts/compare_models.py`, `src/jambandnerd/models/comparison.py`
- Strict audit artifact writes:
  `scripts/audit_shared_model_inputs.py`
- Regression coverage:
  `tests/pipeline/test_compare_models.py`,
  `tests/pipeline/test_audit_shared_model_inputs.py`
- Discoverability/docs:
  `docs/reports/index.md`,
  `docs/reports/model_baselines/README.md`,
  `docs/reference/models/deal.md`
- Durable artifacts:
  `docs/reports/model_baselines/2026-04-07_deal_baseline_goose_last50.json`
  `docs/reports/model_baselines/2026-04-07_shared_model_input_audit.json`
  `docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json`

## Live Validation

- Completed artifact:
  `docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json`
  - `report_status=complete`
  - `completed_bands=["eggy", "billy", "goose", "wsp", "um", "phish"]`
  - promotion gate passed:
    - `avg_recall_k10_beats_ckplus=true`
    - `avg_recall_k25_beats_ckplus=true`
    - `wins_at_least_required_bands_on_recall_k10=true`
    - `no_band_regresses_more_than_0_02_on_recall_k25=true`

- Live backtest consistency check:
  - command:
    `uv run python scripts/run_backtest.py --band goose --model notebook --shows 50`
  - printed aggregate metrics:
    - `K=10: hit_rate=0.940 avg_matches=2.680 precision=0.268 recall=0.212 f1=0.233`
    - `K=25: hit_rate=0.960 avg_matches=4.920 precision=0.197 recall=0.383 f1=0.258`
    - `K=50: hit_rate=0.980 avg_matches=6.660 precision=0.133 recall=0.509 f1=0.210`
  - these match the Goose Notebook metrics already present in the comparison
    workflow output at the same rounded precision.

## Validation Status

- Python formatting/lint/test validation passed for the new comparison/audit
  paths.
- Live Goose baseline, live shared-input audit, live resumable all-band
  baseline, and live Goose Notebook backtest consistency check all completed
  successfully.

## Outcome

- The `last_50` baseline workflow is now operational end to end:
  durable Goose smoke artifact, durable shared-input audit artifact, durable
  resumable all-band artifact, and a live cross-check against
  `scripts/run_backtest.py`.
- This clears the baseline/reliability work needed before starting the first
  constrained Deal ablation batch.

## Next Step

Start Batch 1 Deal ablations against the completed all-band `last_50` baseline,
limited to threshold, recency/decay, gap-stability, and regularization/weighting
experiments with distinct `feature_set_label` values.
