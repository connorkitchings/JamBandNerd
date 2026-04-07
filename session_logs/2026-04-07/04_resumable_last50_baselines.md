# Resumable `last_50` Baselines

## Goal

Make the `last_50` comparison workflow durable for long Deal runs by adding
partial-write/resume behavior, tightening audit artifact writes, and validating
the live baseline commands against the new artifact contract.

## Summary

- Refactored `scripts/compare_models.py` to accumulate results one band at a
  time and atomically write partial JSON reports after each completed band when
  `--output` is provided.
- Added partial-report resume logic keyed off the same output path. The script
  now resumes only `report_status=partial` artifacts and skips already
  completed bands.
- Extended the comparison report schema with `report_status`,
  `requested_bands`, and `completed_bands`.
- Hardened `scripts/audit_shared_model_inputs.py --output` with strict,
  non-empty atomic writes.
- Added report-surface discoverability via `docs/reports/index.md` and
  `docs/reports/model_baselines/README.md`.

## Files Changed

- `scripts/compare_models.py`
- `scripts/audit_shared_model_inputs.py`
- `tests/pipeline/test_compare_models.py`
- `tests/pipeline/test_audit_shared_model_inputs.py`
- `docs/reference/models/deal.md`
- `docs/reports/index.md`
- `docs/reports/model_baselines/README.md`
- `.agent/PLAYBOOK.md`

## Validation

- `./.venv/bin/black --check scripts/compare_models.py scripts/audit_shared_model_inputs.py tests/pipeline/test_compare_models.py tests/pipeline/test_audit_shared_model_inputs.py`
- `uv run ruff check scripts/compare_models.py scripts/audit_shared_model_inputs.py tests/pipeline/test_compare_models.py tests/pipeline/test_audit_shared_model_inputs.py`
- `uv run pytest tests/pipeline/test_compare_models.py tests/pipeline/test_audit_shared_model_inputs.py tests/pipeline/test_evaluate_deal_model.py -q`

## Live Validation

- Refreshed Goose baseline:
  `docs/reports/model_baselines/2026-04-07_deal_baseline_goose_last50.json`
  - now includes `report_status=complete`, `requested_bands`, and
    `completed_bands`
- Revalidated strict audit output:
  `docs/reports/model_baselines/2026-04-07_shared_model_input_audit.json`
- Started the full all-band `last_50` run and interrupted it after Eggy
  completed:
  `docs/reports/model_baselines/2026-04-07_deal_baseline_all_last50.json`
  - verified the partial artifact is valid JSON with
    `report_status=partial` and `completed_bands=["eggy"]`
- Re-ran the exact same all-band command and confirmed the script resumed from
  the partial artifact instead of rescoring Eggy. The live log showed:
  `Resuming partial report ... with completed bands: eggy.`

## Findings

- The resumable baseline workflow works as intended for long-running Deal
  comparisons.
- The full cross-band artifact is still not complete in this session because
  Deal historical retraining remains expensive; the durable partial report is
  now the correct checkpoint for continuing the run later without losing work.
