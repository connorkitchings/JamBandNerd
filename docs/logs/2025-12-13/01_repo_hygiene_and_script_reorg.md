# Session Log: Repo Hygiene, Ops Hardening, and Script Reorg

**Date:** 2025-12-13
**Session:** 01

---

## Task Completed

Improve overall repo cleanliness and operational reliability:
- Fix lint/format issues across the codebase and keep tests green.
- Harden GitHub Actions daily pipeline checks and reduce false negatives.
- Remove unused/broken code and reorganize scripts into clearer buckets.

## Key Outcomes

- **Repo hygiene**
  - `ruff check` + `ruff format` now run clean across `src/`, `scripts/`, `tests/`.
  - Full test suite still passes (`pytest`).
  - Stopped tracking generated build artifacts (`src/jambandnerd.egg-info/*`).

- **Ops hardening**
  - GitHub Actions pipeline updated to be more robust (per-band secrets, WSP-only Playwright install, prediction freshness validation, more reliable data-quality checks, optional Discord notification).

- **Data quality guardrails**
  - WSP normalization drops invalid non-positive song positions to prevent duplicate/garbage setlist rows.
  - WSP collection status logging now includes TourWrangler fallback counts.

- **Aggressive cleanup**
  - Removed unused/broken scripts and unused tracked assets.
  - Reorganized scripts into `scripts/admin/` and `scripts/manual/` while keeping pipeline entrypoints + band collectors in `scripts/` root for dynamic discovery.
  - Added `scripts/README.md` to document where things live.

## Blockers Encountered

None.

## Session Handoff & Next Steps

**First task next dev session:** local testing before pushing anything.

Recommended local smoke tests:
- `uv run python scripts/run_optimized_pipeline.py --band goose --skip-accuracy`
- `uv run streamlit run src/jambandnerd/web/app.py`
- Mobile verification checklist: `docs/operations/mobile_verification.md`

Notes:
- Do **not** push these changes until local pipeline + web flows are confirmed.

## Updated Documents

### Created
- `docs/logs/2025-12-13/01_repo_hygiene_and_script_reorg.md`
- `docs/operations/mobile_verification.md`
- `docs/operations/repo_hygiene_audit.md`
- `scripts/README.md`

### Modified
- `docs/operations/tourwrangler_fallback.md`
- `docs/reports/TEST_REPORT_VALIDATION.md`
- `.github/workflows/daily-pipeline.yml`
- `.gitignore`
- Various code and script files (see git status)
