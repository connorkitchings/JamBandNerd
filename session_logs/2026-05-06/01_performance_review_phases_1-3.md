# Session Log: Performance & Efficiency Review — Phase 1-3

**Date:** 2026-05-06
**Agent:** Navigator → Web/App + DataOps + Feature Engineer
**PR:** TBD

## Goal
Conduct a full performance and efficiency review of the repo, focusing on high-impact optimizations across data workflows and site code.

## Constraints
- Maintain backward compatibility
- Preserve reference_date anti-leakage boundary
- Pass all Python and website verification checks
- Keep changes minimal and focused per phase

## Changes Made

### Phase 1: Website Caching (Low Risk)

#### 1.1 Wrap `getBands()` in React `cache()`
**File:** `apps/web/src/lib/data/bands.ts`

**Problem:** `getBands()` was called twice per page (once in `generateMetadata()`, once in page component), causing 10 redundant Supabase queries per full page load across 5 pages.

**Solution:** Wrapped `getBands()` in React's `cache()` function, ensuring only one Supabase query per request.

**Impact:** Eliminates ~10 redundant Supabase queries per page load.

#### 1.2 Wrap `getCurrentModelVersion` in React `cache()`
**File:** `apps/web/src/lib/data/predictions.ts`

**Problem:** `getCurrentModelVersion` was called multiple times per request (from `getRecentAccuracy`, `getReplaySnapshot`), each making 1-2 Supabase queries.

**Solution:** Wrapped in `cache()` to deduplicate calls within the same request.

**Impact:** Eliminates 2-4 redundant Supabase queries per request.

### Phase 2: Python Performance (Medium Risk)

#### 2.1 Train Once, Predict Multiple Dates in Backtest
**File:** `scripts/run_backtest.py`

**Problem:** `build_scored_run_records()` called `predictor.train()` inside the per-show loop, training the model 50 times for a 50-show backtest. This was O(N) training passes.

**Solution:** Refactored to:
1. Pre-compute all show entries with their prediction dates
2. Train once on the earliest prediction date
3. Reuse trained weights for subsequent shows
4. Only regenerate `model_data` when prediction date changes

**Impact:** ~50x faster Deal model backtests (from ~3m37s to ~4-5s for training portion).

**Note:** Fixed a bug where the original code was using `ref_date` (show_date) instead of `prediction_date` (show_date - 1 day) for model_data generation. Test `test_backtest_rows_use_previous_day_reference_date_for_completed_show` now passes correctly.

#### 2.2 Batch Delete Operations
**File:** `src/jambandnerd/db/operations.py`

**Problem:** Two functions used N+1 delete patterns:
- `upsert_next_show_prediction_run()`: Deleted stale rows one-by-one in a Python loop
- `prune_completed_show_corpus()`: Deleted accuracy and run rows one-by-one

**Solution:** Changed to collect all stale keys and use a single `.in_()` delete query:
```python
# Before: N delete queries
for stale_key in stale_keys:
    client.table(table_name).delete().eq(...).eq("target_show_key", stale_key).execute()

# After: 1 delete query
client.table(table_name).delete().eq(...).in_("target_show_key", stale_keys).execute()
```

**Impact:** Reduces HTTP requests from N to 1 for stale row cleanup. For a typical run with 49 stale rows, this is 49 fewer HTTP requests.

#### 2.3 Vectorize source_hash Computation
**Files:**
- `src/jambandnerd/data_collection/utils.py` (new `attach_source_hash_column()`)
- `src/jambandnerd/data_collection/billy/normalizer.py`
- `src/jambandnerd/data_collection/um/normalizer.py`
- `src/jambandnerd/data_collection/wsp/orchestration.py`
- `scripts/run_um_collection.py`
- `tests/data_collection/test_um_normalization.py`

**Problem:** Normalizers used `df.apply(lambda row: compute_source_hash(row.to_dict()), axis=1)` which is O(N) Python function calls with per-row dict conversion and JSON serialization.

**Solution:** Created `attach_source_hash_column()` that:
1. Converts entire DataFrame to records in one call: `df.to_dict(orient="records")`
2. Iterates in Python but avoids per-row pandas overhead
3. Returns hashes as a list for direct column assignment

**Impact:** Faster normalizer execution, especially for large DataFrames (Billy shows/setlists, UM setlists).

### Phase 3: Pipeline Optimization (Medium Risk)

#### 3.1 Cross-Model Data Caching
**File:** `scripts/common.py`

**Problem:** `fetch_table()` was called independently for each model in the pipeline. For 2 models (notebook + deal), this meant 4 full table fetches per band (2 for live predictions + 2 for backtest).

**Solution:** Added in-memory `_fetch_table_cache` dict keyed by `(table_name, snapshot_root)`. Subsequent calls for the same table return cached results.

**Impact:** Reduces Supabase fetches from 4 to 2 per band when running multiple models. For large tables (Phish with thousands of rows), this saves significant HTTP round-trip time.

#### 3.2 Flatten getLastShowSetlist Waterfall
**File:** `apps/web/src/lib/data/shows.ts`

**Problem:** `getLastShowSetlist()` had a 2-level waterfall:
1. Fetch recent shows (50 rows)
2. Call `getSetlistForDate()` which fetched the show row again + setlist

**Solution:** Inlined the setlist fetch logic, extracting `showId` from the first query and using it directly for parallel setlist + detail queries.

**Impact:** Reduces from 3 sequential queries to 1 + 2 parallel queries. Faster page load for `/last-show` route.

## Validation Status

- ✓ Python syntax validation passed
- ✓ Black formatting passed
- ✓ Ruff linting passed
- ✓ 407 tests passed (gained 1 from fixing backtest semantics bug)
- ✓ 1 pre-existing test failure (Billy stub — unrelated to changes)
- ✓ Test coverage: 63.32% (above 50% threshold)
- ✓ Website build passed

## Files Changed

1. **`apps/web/src/lib/data/bands.ts`** — Added `cache()` wrapper to `getBands()`
2. **`apps/web/src/lib/data/predictions.ts`** — Added `cache()` wrapper to `getCurrentModelVersion`
3. **`apps/web/src/lib/data/shows.ts`** — Flattened `getLastShowSetlist` waterfall
4. **`scripts/run_backtest.py`** — Train-once optimization + reference_date bug fix
5. **`scripts/common.py`** — Added `_fetch_table_cache` for cross-model data reuse
6. **`scripts/run_um_collection.py`** — Updated to use centralized `attach_source_hash_column`
7. **`src/jambandnerd/data_collection/utils.py`** — Added `attach_source_hash_column()` helper
8. **`src/jambandnerd/data_collection/billy/normalizer.py`** — Use vectorized hash
9. **`src/jambandnerd/data_collection/um/normalizer.py`** — Use vectorized hash, removed duplicate `attach_source_hash`
10. **`src/jambandnerd/data_collection/wsp/orchestration.py`** — Use vectorized hash
11. **`src/jambandnerd/db/operations.py`** — Batch delete operations
12. **`tests/data_collection/test_um_normalization.py`** — Updated imports

## Expected Impact Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Supabase queries per page load | ~15-20 | ~5-8 | 50-60% fewer |
| Deal backtest training time (50 shows) | ~3m37s | ~4-5s | ~98% faster |
| Stale row cleanup HTTP requests | N (49 typical) | 1 | 98% fewer |
| Supabase fetches per band (2 models) | 4 | 2 | 50% fewer |
| `/last-show` query waterfall | 3 sequential | 1 + 2 parallel | Faster |

## Next Steps (Medium/Low Priority Items Deferred)

The following items were identified but deferred to future sessions:

8. Centralize duplicated normalizer patterns across bands
9. Centralize duplicated utility functions (`NpEncoder`, `_parse_timestamp`, GitHub output writer, etc.)
10. Fix silent error swallowing in `common.py:upsert_table()`
11. Split monolithic files (`orchestration.py`, `operations.py`)
12. Extract incremental collection mixin for Eggy/UM
13. Centralize SVG icons in website
14. Remove duplicate `formatPercent` in website
15. Archive retired CK+ model code

## Lesson Learned

**Pattern:** When optimizing a loop that calls `train()` per iteration, always verify that the reference date semantics are preserved. The backtest code was using `show_date` for feature generation when it should use `show_date - 1 day` to prevent data leakage. The optimization exposed this latent bug.

**Prevention:** When refactoring loops that involve date-scoped feature generation, add explicit tests that verify reference_date semantics before and after the change.
