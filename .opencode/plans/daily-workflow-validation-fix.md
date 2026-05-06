# Plan: Fix Daily Workflow Validation Failures

## Problem
The daily pipeline workflow failed on May 6th and 7th, 2026 for 4 bands (phish, goose, eggy, wsp). All failures occurred at the "Validate Prediction Tables" step after predictions were successfully generated.

## Root Cause Analysis
Based on code review, the validation script (`scripts/validate_prediction_tables.py`) checks:
1. Freshness of predictions in `next_show_prediction_runs` (max 72h old)
2. Projection integrity in `next_show_prediction_songs` (row count and top_song match)
3. Stale projection rows older than 72h

The current error messages are ambiguous - they don't include the model_slug, making it impossible to tell which model (notebook or deal) is failing or why.

## Changes Required

### 1. Enhanced Diagnostic Logging in `scripts/validate_prediction_tables.py`

**File**: `scripts/validate_prediction_tables.py`

**Changes**:
- Add `model_slug` to all failure messages (e.g., `[FAIL] {band}/{model_slug}: ...`)
- Add context to projection mismatch errors (expected vs actual row count, top_song values)
- Add model_version to stale projection messages
- Add summary line showing which specific check failed

**Lines to modify**:
- Line 81: Add model_slug to missing reference_date error
- Line 91-93: Add expected row count and top_song context to missing projection error
- Line 97-99: Add reference_date to row count mismatch error
- Line 107-109: Add reference_date and quoted values to top_song mismatch error
- Line 133-137: Add model_version to stale projection messages

### 2. Verify No Other Issues

After adding logging, the next workflow run will surface the exact failure mode. Based on findings, potential follow-up fixes:
- If projection rows are missing: investigate `replace_next_show_prediction_projection` delete/insert logic
- If stale rows exist: verify cleanup logic in projection replacement
- If reference_date mismatch: check deal model's training logic for date drift

## Testing
- Run `npm run verify:python` to ensure code quality
- No test changes needed (diagnostic-only change)
- Next daily workflow run will produce actionable error messages

## Risks
- None: this is a logging-only change that doesn't affect behavior
