# Model Comparison Framework + Deal Baseline Infrastructure

## Goal

Implement a reusable model-comparison framework for experimental models, align
Deal evaluation semantics with the shared backtest rule, and update docs so the
repo reflects the actual `deal_v2` implementation.

## Summary

- Added a registry-driven comparison workflow via `scripts/compare_models.py`
  plus shared scoring/report helpers under `src/jambandnerd/models/`.
- Aligned historical scoring to one conservative rule: score each target show
  from the prior calendar day so same-day and double-header data cannot leak
  into features.
- Updated Deal training-frame generation to follow that rule and added a
  regression test for same-day leakage.
- Added `scripts/audit_shared_model_inputs.py` so future feature work can audit
  normalized shared-field availability before expanding the cross-band model
  contract.
- Rewrote the Deal reference docs to match the current `deal_v2` logistic
  implementation and removed the stale `xgboost` dependency from `pyproject.toml`.

## Files Changed

### Comparison framework

- `src/jambandnerd/models/evaluation.py`
- `src/jambandnerd/models/comparison.py`
- `scripts/compare_models.py`
- `scripts/evaluate_deal_model.py`

### Deal / backtest alignment

- `src/jambandnerd/models/deal/features.py`
- `scripts/run_backtest.py`
- `src/jambandnerd/models/deal/__init__.py`

### Shared-input audit

- `scripts/audit_shared_model_inputs.py`

### Tests

- `tests/models/test_deal_model.py`
- `tests/pipeline/test_compare_models.py`
- `tests/pipeline/test_evaluate_deal_model.py`
- `tests/pipeline/test_audit_shared_model_inputs.py`

### Docs / metadata

- `docs/contributor/model_development.md`
- `docs/reference/specifications/cli.md`
- `docs/reference/models/deal.md`
- `docs/reference/models/index.md`
- `docs/contributor/developer_guide/architecture.md`
- `docs/overview/implementation_status.md`
- `scripts/README.md`
- `pyproject.toml`

## Validation

- `./.venv/bin/black --check src/jambandnerd/models/comparison.py src/jambandnerd/models/evaluation.py src/jambandnerd/models/deal/features.py src/jambandnerd/models/deal/__init__.py scripts/compare_models.py scripts/evaluate_deal_model.py scripts/run_backtest.py scripts/audit_shared_model_inputs.py tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py tests/pipeline/test_run_backtest.py tests/pipeline/test_audit_shared_model_inputs.py`
- `./.venv/bin/ruff check src/jambandnerd/models/comparison.py src/jambandnerd/models/evaluation.py src/jambandnerd/models/deal/features.py src/jambandnerd/models/deal/__init__.py scripts/compare_models.py scripts/evaluate_deal_model.py scripts/run_backtest.py scripts/audit_shared_model_inputs.py tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py tests/pipeline/test_run_backtest.py tests/pipeline/test_audit_shared_model_inputs.py`
- `uv run pytest tests/models/test_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py tests/pipeline/test_run_backtest.py tests/pipeline/test_audit_shared_model_inputs.py -q`

## Environment Notes

- Attempted live comparison run:
  - `uv run python scripts/compare_models.py --candidate-model deal --band all --fresh-training --include-candidate-diagnostics --output /tmp/deal_comparison_report.json`
- Attempted narrow live comparison run:
  - `uv run python scripts/compare_models.py --candidate-model deal --band goose --window 50 --fresh-training --output /tmp/deal_goose_comparison_report.json`
- In this shell both live runs stalled without emitting a report file or an
  actionable exception, so the framework is implemented and test-covered but the
  first real Supabase-backed baseline still needs an environment-backed rerun.
