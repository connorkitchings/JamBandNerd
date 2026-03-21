# 2026-03-21 Session Log 04

## Goal
Implement the next Supabase stabilization steps: safer derived-data rebuilds, explicit accuracy validation, and better WSP missing-setlist diagnostics that distinguish upstream source lag from collector failures.

## What Changed
- Added `scripts/validate_accuracy_tables.py` to validate per-show and aggregate accuracy freshness using `evaluated_at`.
- Updated `scripts/rebuild_derived_data.py` to clear outputs just-in-time per model instead of clearing everything upfront, and added explicit phase logging plus post-rebuild accuracy validation.
- Updated `scripts/run_optimized_pipeline.py` to validate accuracy tables after the existing prediction validation step.
- Added WSP missing-setlist classification in `src/jambandnerd/data_collection/wsp/orchestration.py` so recent gaps are categorized as upstream-missing, collector-missed, request-failed, or fallback-available.
- Extended `CollectionStatus` to surface those WSP missing-setlist diagnostics in the success summary.
- Updated `scripts/diagnose_band_data.py` so WSP upstream-missing setlists show as warnings instead of audit failures.
- Updated `.github/workflows/daily-pipeline.yml`, `scripts/README.md`, and `docs/operations/github_actions.md` to include the new accuracy validation path.

## Verification
- `uv run pytest tests/test_validate_accuracy_tables.py tests/test_operational_recovery_scripts.py tests/test_data_diagnostics_scripts.py tests/data_collection/test_wsp_orchestration.py tests/pipeline/test_run_optimized_pipeline.py`
- `uv run ruff check scripts/validate_accuracy_tables.py scripts/rebuild_derived_data.py scripts/run_optimized_pipeline.py scripts/diagnose_band_data.py src/jambandnerd/data_collection/wsp/orchestration.py src/jambandnerd/data_collection/wsp/status.py tests/test_validate_accuracy_tables.py tests/test_operational_recovery_scripts.py tests/test_data_diagnostics_scripts.py tests/data_collection/test_wsp_orchestration.py tests/pipeline/test_run_optimized_pipeline.py`
- `uv run python scripts/validate_accuracy_tables.py --band eggy --band um --max-age-hours 72`
- `uv run python scripts/diagnose_band_data.py --band wsp --verbose`
- `uv run python scripts/audit_raw_data.py --band all`

## Outcome
- Raw-data audit now reports `Bands with issues: 0` and treats the WSP `2026-03-20` gap as an upstream warning instead of a system failure.
- Accuracy validation now exists as a first-class operational check for rebuilds, the optimized runner, and GitHub Actions.
- Large rebuilds are safer because one model can fail without pre-clearing all other band/model outputs first.

## Follow-Up
- The WSP warning will remain until Everyday Companion or a backup source publishes a usable setlist for `show_id=22455`.
- The pre-existing unrelated changes in `apps/web` remain in the worktree and were not modified by this session.
