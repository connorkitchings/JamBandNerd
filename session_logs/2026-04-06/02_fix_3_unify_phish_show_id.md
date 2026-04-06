# Fix 3: Unify Phish `show_id`

**Date**: 2026-04-06
**Branch**: `fix/unify-phish-show-id` → merged to `dev`

---

## Summary

Phish was the only band using `api_show_id` as its show primary key column. All other bands use `show_id`. This fix aligns Phish with the shared convention, removing all band-specific conditionals.

Since Phish data is fully recoverable via the phish.net API, a clean break approach was used instead of a multi-step migration window.

## Files Changed

- **`src/jambandnerd/config/bands.py`**: `"phish": "api_show_id"` → `"phish": "show_id"`
- **`scripts/run_phish_collection.py`**: `_normalize_shows()` and `_normalize_setlists()` now write `show_id` instead of `api_show_id`. Conflict column updated.
- **`scripts/run_live_tracker.py`**: Removed `if band == "phish"` conditional for `show_id_col`. All bands now use `"show_id"` unconditionally.
- **`scripts/get_last_completed_show_date.py`**: Removed `id_col = "api_show_id" if band == "phish" else "show_id"`. Uses `"show_id"` for all bands.
- **`src/jambandnerd/transformations/normalization.py`**: Removed `"api_show_id"` from `show_id_candidates` fallback tuple.
- **`tests/pipeline/fixtures.py`**: Removed conditional `show_id_key` — all bands use `"show_id"`.
- **`tests/pipeline/test_normalization_contract.py`**: Updated Phish test data to use `show_id` instead of `api_show_id`.
- **`supabase/migrations/20260406_unify_phish_show_id.sql`**: Renames `api_show_id` → `show_id` in `phish_shows_raw` and `phish_setlists_raw`, updates `bands` registry.

## Verification

- `uv run black src tests scripts` — clean
- `uv run ruff check src tests scripts` — clean
- `uv run pytest` — 170 passed, 6 skipped, 1 pre-existing failure
- Zero remaining `api_show_id` references in Python codebase

## Post-Deploy Steps

1. **Run Supabase migration**: `20260406_unify_phish_show_id.sql`
2. **Re-collect Phish data**: `uv run python scripts/run_phish_collection.py --full-backfill`
3. **Verify**: `uv run python scripts/get_last_completed_show_date.py --band phish`
