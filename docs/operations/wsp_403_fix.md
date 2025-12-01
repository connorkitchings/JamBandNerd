# WSP 403 Forbidden Fix

**Date**: 2025-12-01
**Issue**: WSP data collection succeeds locally but fails in GitHub Actions with 403 Forbidden errors
**Status**: Fixed - Ready for testing

## Problem Summary

The WSP collector was experiencing "403 Forbidden" errors when running in GitHub Actions, causing the daily pipeline to fail. The errors manifested as:

```
HTTPSConnectionPool(host='www.everydaycompanion.com', port=443):
Max retries exceeded with url: /setlists/20251229a.asp
(Caused by ResponseError('too many 403 error responses'))
```

### Root Causes

1. **403 in retry list** - The retry strategy included 403 in `status_forcelist`, causing urllib3 to retry access-denied errors and eventually fail with "too many 403 error responses"

2. **GitHub Actions IP detection** - everydaycompanion.com likely blocks known GitHub Actions IP ranges while allowing residential IPs

3. **Insufficient rate limiting** - 2-second delays between requests were adequate locally but too aggressive for automated CI runs

4. **Poor error handling** - 403 errors were causing the entire collection to fail rather than gracefully falling back to TourWrangler

## Solutions Implemented

### 1. Removed 403 from Retry List

**File**: `src/jambandnerd/data_collection/wsp/session.py:48`

**Change**:
```python
# BEFORE
status_forcelist=[403, 429, 500, 502, 503, 504]

# AFTER
status_forcelist=[429, 500, 502, 503, 504]
```

**Rationale**: 403 (Forbidden) is an access denial, not a transient error. Retrying immediately makes the problem worse by triggering "too many 403 error responses" in urllib3. Transient errors (429, 500, 502, 503, 504) should be retried; permission errors should not.

### 2. CI-Aware Rate Limiting

**File**: `src/jambandnerd/data_collection/wsp/session.py:63-67`

**Change**:
```python
# Detect if running in GitHub Actions
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS") == "true"
rate_limit_delay = 6.0 if IS_GITHUB_ACTIONS else 2.0
```

**Rationale**: GitHub Actions IPs are often more aggressively rate-limited by websites. Using 6-second delays (3x local delays) reduces the likelihood of triggering anti-bot detection.

### 3. Enhanced Jitter for CI

**File**: `src/jambandnerd/data_collection/wsp/session.py:76-77`

**Change**:
```python
# Use larger jitter in CI to appear more human-like
jitter_range = 2.0 if IS_GITHUB_ACTIONS else 0.5
delay_with_jitter = rate_limit_delay + random.uniform(0, jitter_range)
```

**Rationale**: Human users don't make requests at perfectly regular intervals. Adding 0-2 second random variation in CI (vs 0-0.5s locally) makes the request pattern less bot-like.

**Result**: In CI, requests are spaced 6-8 seconds apart (6s base + 0-2s jitter)

### 4. Graceful 403 Handling

**File**: `src/jambandnerd/data_collection/wsp/collector.py:83-96`

**Change**:
```python
except requests.exceptions.HTTPError as e:
    if e.response and e.response.status_code == 403:
        self.status.record_403_error(show_url)
        logger.warning(
            f"403 Forbidden for {show_url}. Skipping EC scrape for this show. "
            f"(Total 403s: {self.status.http_403_errors})"
        )
        return []  # Skip this show, TourWrangler fallback will handle it
```

**Rationale**: Instead of crashing the entire collection on 403, skip individual shows and let the TourWrangler fallback (already implemented in `orchestration.py`) handle them. This graceful degradation means partial 403 errors don't cause complete failures.

## How It Works Now

### Normal Operation (No 403s)
1. Collect shows from EC
2. Scrape setlists from EC with 6-8s delays in CI
3. Insert data with `source = 'everydaycompanion'`
4. Check for missing recent shows (already complete)
5. Success ✅

### Partial 403s (Some Shows Blocked)
1. Collect shows from EC
2. Scrape setlists, some return 403
3. **Skip 403 shows** (log warning, don't crash)
4. Insert successful data with `source = 'everydaycompanion'`
5. TourWrangler fallback detects missing shows
6. **TourWrangler fills gaps** with `source = 'tourwrangler'`
7. Success ✅ (with warnings)

### Complete 403 Block (All Shows Blocked)
1. Collect shows from EC (usually works - different endpoint)
2. All setlist scrapes return 403
3. Skip all shows, insert 0 setlist rows
4. **Status tracker detects failure**: `http_403_errors > 0 && setlists_collected == 0`
5. TourWrangler fallback detects all recent shows are missing
6. **TourWrangler fills all gaps**
7. Partial success ✅ or controlled failure with clear error message

## Testing Plan

### Local Testing (Should Still Work)
```bash
# Should complete successfully with 2s delays
uv run python scripts/run_wsp_collection.py
```

**Expected**: Same behavior as before, 2-second delays, no change in success rate

### CI Testing (GitHub Actions)
```bash
# Manually trigger workflow for WSP only
gh workflow run daily-pipeline.yml -f band=wsp -f skip_accuracy=true
```

**Expected outcomes**:

**Best case**: No 403 errors, slower but successful collection (6-8s delays)
- Shows collected: ✅
- Setlists collected: ✅
- Source: `everydaycompanion`

**Likely case**: Some 403 errors, mixed EC + TW data
- Shows collected: ✅
- Some setlists from EC: ✅
- Remaining setlists from TW: ✅
- Sources: Mixed `everydaycompanion` and `tourwrangler`

**Worst case**: All 403 errors, TW-only data
- Shows collected: ✅
- Setlists from EC: ❌ (all 403)
- All setlists from TW: ✅
- Source: `tourwrangler` only

### Monitoring After Deployment

Watch these metrics in daily runs:

1. **403 error count** - Should be lower, ideally 0
2. **Collection success rate** - Should improve
3. **TourWrangler usage** - May increase temporarily if EC still blocks
4. **Data completeness** - Should remain 100% (EC + TW coverage)

### Rollback Plan

If the fix doesn't work:

1. Revert `session.py` changes
2. Set `GITHUB_ACTIONS` check to always use `IS_GITHUB_ACTIONS = True` (force CI mode locally to test)
3. Consider alternative strategies:
   - Use TourWrangler as primary in CI
   - Implement request proxying
   - Use different user agent strings
   - Add session warming (initial requests before scraping)

## Additional Improvements (Future)

If 403s persist after this fix:

### Short-term:
- **Batch delays**: Pause 30s every 10 requests in CI
- **Session warming**: Make initial requests to establish cookies before scraping
- **User agent rotation**: Vary UA strings slightly between requests

### Medium-term:
- **TourWrangler-first in CI**: Use TW as primary source in GitHub Actions, EC as verification
- **Request proxying**: Route CI requests through proxy service
- **Scheduled staggering**: Spread band collections throughout the day instead of parallel

### Long-term:
- **API partnership**: Contact everydaycompanion.com about official API access
- **Data donation**: Contribute cleaned data back to community

## Files Changed

1. `src/jambandnerd/data_collection/wsp/session.py` - Retry strategy and rate limiting
2. `src/jambandnerd/data_collection/wsp/collector.py` - 403 error handling
3. `docs/operations/wsp_403_fix.md` - This documentation

## References

- Original issue: GitHub Actions WSP collection failures
- TourWrangler fallback: `src/jambandnerd/data_collection/wsp/orchestration.py:207-296`
- Status tracking: `src/jambandnerd/data_collection/wsp/status.py`
- Collection status logic: `status.should_fail()` determines exit code

---

**Next Steps**:
1. Commit changes
2. Test locally to ensure no regression
3. Deploy to GitHub Actions
4. Monitor daily runs for 1 week
5. Document results
