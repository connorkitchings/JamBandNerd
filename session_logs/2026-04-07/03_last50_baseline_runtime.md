# Last-50 Comparison Scope + Runtime Baseline

## Goal

Narrow the new model-comparison framework to the active `last_50` scope, remove
the `all_history` comparison path, regenerate the durable Goose baseline, and
capture the runtime shape of the first full cross-band `last_50` Deal baseline.

## Summary

- Removed `all-history` from `scripts/compare_models.py` and made `last_50` the
  only default comparison window.
- Updated comparison tests and active docs so the current comparison contract is
  numeric-window only and `last_50` is the standard baseline scope.
- Added per-show comparison progress logging so fresh-trained Deal runs no
  longer appear stalled during long historical scoring loops.
- Regenerated the durable Goose comparison artifact:
  `docs/reports/model_baselines/2026-04-07_deal_baseline_goose_last50.json`
- Generated the durable shared-input audit artifact:
  `docs/reports/model_baselines/2026-04-07_shared_model_input_audit.json`

## Files Changed

- `scripts/compare_models.py`
- `src/jambandnerd/models/comparison.py`
- `scripts/evaluate_deal_model.py`
- `tests/pipeline/test_compare_models.py`
- `docs/reference/models/deal.md`
- `docs/contributor/model_development.md`
- `docs/reference/specifications/cli.md`
- `scripts/README.md`
- `.agent/PLAYBOOK.md`

## Validation

- `./.venv/bin/black --check src/jambandnerd/models/comparison.py scripts/compare_models.py scripts/evaluate_deal_model.py tests/pipeline/test_compare_models.py`
- `uv run ruff check src/jambandnerd/models/comparison.py scripts/compare_models.py scripts/evaluate_deal_model.py tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py`
- `uv run pytest tests/pipeline/test_compare_models.py tests/pipeline/test_evaluate_deal_model.py -q`

## Live Artifacts

- Goose last-50 baseline:
  `docs/reports/model_baselines/2026-04-07_deal_baseline_goose_last50.json`
- Shared-input audit:
  `docs/reports/model_baselines/2026-04-07_shared_model_input_audit.json`

## Findings

- Goose `last_50` baseline remains strong versus CK+ at `recall@10` and
  `recall@25`, but still trails Notebook slightly on Goose.
- The shared-input audit shows `venue_name` is universal across all active
  bands, while `city`, `state`, and `country` are not.
- A full cross-band `last_50` Deal baseline is operationally valid but slow:
  Eggy took about five minutes for Deal's 50-show historical pass, and Billy
  was materially slower. The serial all-band run should be treated as a
  long-running experiment job, not a quick validation command.
- The live all-band run was interrupted during Billy `show 20/50`; the
  traceback confirmed the bottleneck is repeated Deal historical feature
  generation in `src/jambandnerd/models/deal/features.py` via
  `generate_deal_features()` / `build_training_frame()`, not Supabase fetch or
  JSON report writing.
