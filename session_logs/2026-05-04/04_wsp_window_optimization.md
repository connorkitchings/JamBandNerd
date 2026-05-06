# Session Log: WSP Collection Window Optimization

**Date:** 2026-05-04
**Agent:** DataOps
**PR:** #108

## Goal
Fix WSP daily collection taking 10 minutes by aligning the collection window with the configured 90-day rolling policy instead of the hardcoded 2-year window.

## Constraints
- Maintain backward compatibility with --year_start/--year_end args
- Preserve full_backfill behavior
- Keep changes minimal and focused
- Pass all Python validation checks

## Commands Run

```bash
# Validation
npm run verify:python  # ✓ All checks passed

# Syntax verification
python3 -m py_compile scripts/run_wsp_collection.py
python3 -m py_compile src/jambandnerd/data_collection/wsp/orchestration.py

# Git workflow
git add scripts/run_wsp_collection.py src/jambandnerd/data_collection/wsp/orchestration.py
git commit -m "fix(wsp): align collection window with 90-day rolling policy"
git pull origin dev --rebase
git push origin dev
gh pr create --base main --head dev --title "fix(wsp): align collection window with 90-day rolling policy"
```

## Files Changed

1. **`scripts/run_wsp_collection.py`**
   - Added import: `get_collection_policy` from bands config
   - Changed default window from 2 years to 90 days (from policy)
   - Added date range calculation: `start_date = today - 90 days`, `end_date = today + 90 days`
   - Pass `start_date` and `end_date` to `process_wsp_data()`
   - Updated docstring comment to reflect new default behavior

2. **`src/jambandnerd/data_collection/wsp/orchestration.py`**
   - Added `start_date` and `end_date` parameters to `process_wsp_data()` signature
   - Modified show collection to use date-based filtering when available
   - Added date-based query for fetching shows from DB (prioritized over year-based)
   - Maintained backward compatibility with year_start/year_end args

## Validation Status

- ✓ Python syntax validation passed
- ✓ Ruff linting and formatting passed
- ✓ Black formatting passed
- ✓ Pre-commit hooks passed
- ✓ PR #108 created successfully

## Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Window | 2 years (2024-2025) | 90 days + upcoming | 80% smaller |
| Shows processed | ~74 | ~15 | 80% reduction |
| Collection time | ~10 minutes | ~3-4 minutes | 60% faster |

## Root Cause

WSP was hardcoding a 2-year window in `run_wsp_collection.py` instead of reading `rolling_window_days=90` from the collection policy in `bands.py`. This caused daily runs to process 74 shows instead of ~15.

## Testing Checklist (Post-Merge)

- [ ] Log shows: "Defaulting to show collection window: YYYY-MM-DD to YYYY-MM-DD"
- [ ] Log shows: "Fetching shows from database for date range..."
- [ ] Log shows: "Starting setlist collection for ~15 shows" (not 74)
- [ ] Total WSP time: ~3-4 minutes (not 9-10 minutes)

## Next Step

Monitor next daily pipeline run for PR #108 to verify ~15 shows processed and ~3-4 minute runtime.

## Lesson Learned

**Pattern:** Collection policy configuration (`rolling_window_days`) must be actively consumed by runner scripts, not just defined. Hardcoded defaults in runners can silently override policy intent.

**Prevention:** Audit all collection runners to ensure they read from `get_collection_policy()` rather than hardcoding window logic.
