# Repo Hygiene Audit (Code + Scripts)

**Last Updated:** 2025-12-13

This note captures repo hygiene cleanups and remaining follow-ups for unused/unnecessary code.

## Completed cleanups

- **Lint/format baseline fixed**: `ruff check` and `ruff format` run clean across `src/`, `scripts/`, `tests/`.
- **Removed broken/obsolete script**: deleted `scripts/run_phish_backtest.py` (superseded by `scripts/run_backtest.py`).
- **Removed unused Cosmic collector scaffold**:
  - Deleted `src/jambandnerd/data_collection/cosmic/`
  - Updated `src/jambandnerd/data_collection/__init__.py` to match `SUPPORTED_BANDS` (6-band system).
- **Removed unused tracked assets**:
  - Deleted `web/Images/*` (unreferenced images)
  - Deleted `livewire.min.js` (unreferenced local copy)
- **Moved ad-hoc package “test script” out of `src/`**:
  - Removed `src/jambandnerd/data_collection/test_enhanced_collectors.py`
  - Added `scripts/manual/test_enhanced_collectors.py` for manual debugging.
- **Removed unused stub CLI**: deleted `scripts/run_model.py` (was a placeholder and not wired to pipeline).
- **Removed unused Goose-only helper**: deleted `scripts/get_latest_show.py` (superseded by `scripts/get_last_completed_show_date.py`).
- **Reorganized non-core scripts**:
  - Admin tools moved under `scripts/admin/`
  - WSP fallback utilities moved under `scripts/manual/wsp/`
  - Validation test scripts moved under `scripts/manual/validation/`
  - One-off Goose transformations moved under `scripts/manual/goose/`
  - Misc data-quality checks moved under `scripts/manual/`

## Remaining “manual / one-off” scripts (not part of pipeline)

These appear intentional, but could be grouped later to reduce top-level `scripts/` clutter:

- **Diagnostics (kept top-level for convenience)**: `scripts/diagnose_band_data.py`
- **Admin**: `scripts/admin/add_setlist.py`, `scripts/admin/delete_setlist_data.py`, `scripts/admin/get_schemas.py`
- **WSP fallback tooling**: `scripts/manual/wsp/tw_compare_ec_tw.py`, `scripts/manual/wsp/tw_fallback_test.py`
- **Validation reports (referenced in docs)**:
  - `scripts/manual/validation/test_validation_warnings.py`
  - `scripts/manual/validation/test_validation_comprehensive.py`

## Suggested follow-ups (optional)

- Add a short `scripts/README.md` that classifies scripts into pipeline entrypoints vs collectors vs admin/manual tools.
