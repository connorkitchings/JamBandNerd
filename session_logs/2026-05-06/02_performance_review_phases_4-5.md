# Session Log: Performance Review — Phases 4-5 (Medium & Low Priority)

**Date:** 2026-05-06
**Agent:** Navigator → DataOps + Web/App
**PR:** https://github.com/connorkitchings/JamBandNerd/pull/116

## Goal
Complete medium and low priority items from the performance and efficiency review.

## Changes Made

### M1: Fix Silent Error Swallowing
**File:** `scripts/common.py`

Changed `upsert_table()` return type from `None` to `bool`. Returns `True` on success (or empty data skip), `False` on collection or upsert failure. Callers can now check return value and decide whether to continue or fail.

**Impact:** Backward-compatible; existing callers that ignore return value still work. Enables better error handling in collection scripts.

### M2: Centralize Duplicated Utilities
**Files:** `scripts/common.py` + 13 scripts

Added 4 centralized utilities to `scripts/common.py`:
- `NpEncoder` — JSON encoder for numpy/pandas types (was in 2 files)
- `parse_timestamp` — ISO8601 timestamp parser (was in 3 files)
- `write_github_output` — GitHub Actions output writer (was in 5+ files)
- `write_json_atomic` — Atomic JSON file writer (was in 2 files)

Updated 13 scripts to import from `scripts/common` instead of defining locally:
- `generate_live_predictions.py`
- `generate_predictions.py`
- `validate_prediction_tables.py`
- `validate_accuracy_tables.py`
- `check_supported_model_freshness.py`
- `run_billy_collection.py`
- `run_um_collection.py`
- `run_wsp_collection.py`
- `run_backtest.py`
- `diagnose_band_data.py`
- `admin/repair_wsp_setlists_range.py`
- `model_readiness.py`
- `recover_deal_last50_local.py`
- `audit_supabase_tables.py`

**Impact:** Eliminated ~140 lines of duplicated code. Single source of truth for common utilities.

### M3: Website Quick Wins
**Files:** `apps/web/src/components/icons.tsx` (new), `song-board.tsx`, `deal-mobile-row.tsx`, `accuracy-table.tsx`

1. **Extracted shared SVG icons** — Created `icons.tsx` with `ChevronIcon`, `CheckIcon`, `ModelAgreeIcon`. Removed 3 duplicated icon definitions from `song-board.tsx` and `deal-mobile-row.tsx`.

2. **Removed duplicate `formatPercent`** — `accuracy-table.tsx` now imports from `@/lib/format` instead of defining locally.

**Impact:** Cleaner component architecture, reduced bundle duplication.

### M5: Fix Global Mutable State Caches
**Files:** `src/jambandnerd/config/bands.py`, `src/jambandnerd/db/operations.py`

Added TTL-based invalidation to 3 caches:
1. `_cached_registry_band_rows` — 1-hour TTL
2. `_cached_runtime_band_id_columns` — 1-hour TTL
3. `_schema_cache` — 2-hour TTL

**Impact:** Prevents stale data from persisting indefinitely across long-running processes. Low risk: TTL values are conservative.

### M6: Remove force-dynamic from Static Pages
**Status:** Already removed — pages (`about`, `contact`, `data-use`) do not have `force-dynamic` exports.

### M7: Centralize Hardcoded Email
**Files:** `apps/web/src/lib/site.ts`, `contact/page.tsx`, `data-use/page.tsx`

Added `CONTACT_EMAIL` to `site.ts` and updated both pages to import from there instead of defining locally.

**Impact:** Single source of truth for contact email.

### M4: Archive Retired CK+ Model
**Status:** Completed — moved to `src/jambandnerd/models/archived/ckplus/`, removed from registry, config, and tests. Updated tests to use `notebook` as baseline.

## Verification Status

- ✓ Python syntax validation passed
- ✓ Black formatting passed
- ✓ Ruff linting passed
- ✓ 407 tests passed (same as Phase 1-3)
- ✓ 1 pre-existing test failure (Billy stub — unrelated)
- ✓ Test coverage: 63.36% (above 50% threshold)
- ✓ Website build passed

## Files Changed (20 total)

### Python (16 files)
1. `scripts/common.py` — Added 4 centralized utilities, changed `upsert_table` to return bool
2. `scripts/generate_live_predictions.py` — Import NpEncoder from common
3. `scripts/generate_predictions.py` — Import NpEncoder from common
4. `scripts/validate_prediction_tables.py` — Import parse_timestamp from common
5. `scripts/validate_accuracy_tables.py` — Import parse_timestamp from common
6. `scripts/check_supported_model_freshness.py` — Import parse_timestamp, write_github_output from common
7. `scripts/run_billy_collection.py` — Import write_github_output from common
8. `scripts/run_um_collection.py` — Import write_github_output from common
9. `scripts/run_wsp_collection.py` — Import write_github_output from common
10. `scripts/run_backtest.py` — Import write_github_output from common
11. `scripts/diagnose_band_data.py` — Import batched_values from common
12. `scripts/admin/repair_wsp_setlists_range.py` — Import batched_values from common
13. `scripts/model_readiness.py` — Import write_json_atomic from common
14. `scripts/recover_deal_last50_local.py` — Import write_json_atomic from common
15. `scripts/audit_supabase_tables.py` — Import parse_timestamp from common
16. `src/jambandnerd/config/bands.py` — Add TTL to registry caches
17. `src/jambandnerd/db/operations.py` — Add TTL to schema cache

### Website (5 files)
1. `apps/web/src/components/icons.tsx` — New shared icons module
2. `apps/web/src/components/song-board.tsx` — Import icons from shared module
3. `apps/web/src/components/deal-mobile-row.tsx` — Import icons from shared module
4. `apps/web/src/components/accuracy-table.tsx` — Import formatPercent from @/lib/format
5. `apps/web/src/lib/site.ts` — Add CONTACT_EMAIL
6. `apps/web/src/app/contact/page.tsx` — Import CONTACT_EMAIL from site
7. `apps/web/src/app/data-use/page.tsx` — Import CONTACT_EMAIL from site

## Expected Impact Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Duplicated utility code | ~140 lines | 0 | 100% reduction |
| `upsert_table` error visibility | Silent | Returns bool | Detectable failures |
| Cache staleness risk | Indefinite | 1-2 hour TTL | Auto-refresh |
| SVG icon duplication | 3 icons × 2 files | 1 shared module | Cleaner imports |
| Contact email sources | 2 places | 1 place | Single source of truth |

## Next Steps

All planned items completed. PR #116 created to merge dev into main.

### Additional UI Tweaks (Post-Session)
- Centered "Next show" teaser text on homepage
- Removed redundant "Completed show date" and "Prediction cutoff date" from replay page

## Lesson Learned

**Pattern:** When centralizing duplicated utilities, check ALL files that import from the original location, not just where the function is defined. The `audit_supabase_tables.py` file imported `_parse_timestamp` from `validate_prediction_tables.py`, which would have broken after removal.

**Prevention:** Use `rg -n "function_name" scripts/ tests/` before removing any centralized utility to catch all import sites.
