# Validation Improvements - Summary

## Overview

This document summarizes the improvements made to the data validation and collection pipeline to make it more robust and resilient for all supported bands (Goose, Phish, WSP).

## Problem Statement

Previously, the data collection scripts would fail silently or block data inserts when validation detected type mismatches or other non-critical schema issues. This caused the GitHub Actions workflow to fail and prevented fresh data from being inserted into the database, even when the data quality issues were minor and acceptable.

## Solution

We implemented a **warning-only validation** approach across all band collection scripts and updated the GitHub Actions workflow accordingly.

## Changes Made

### 1. Validation Module (`src/jambandnerd/db/validation.py`)

**Already implemented** (from previous work):
- Made validation permissive by default
- Only fails on missing required columns or nullability violations
- Type mismatches and other issues are logged as warnings but don't block inserts
- This allows data to be inserted even with minor schema discrepancies

### 2. Band Collection Scripts

Updated all three band collection scripts to use warning-only validation:

#### Goose (`scripts/run_goose_collection.py`)
- Changed validation failure handling to print warnings instead of returning early
- Now proceeds with upsert even when validation reports issues
- Shows clear warning messages with emoji indicators (⚠️)
- Details which validation issues occurred (missing columns, type mismatches, nullable violations)

#### Phish (`scripts/run_phish_collection.py`)
- Updated the `upsert_table` helper function to use warning-only validation
- Logs validation warnings using the `logging` module
- Proceeds with data insertion even when validation finds issues
- Same detailed warning format as Goose

#### WSP (`scripts/run_wsp_collection.py`)
- Added `skip_validation` parameter to function signature
- Added validation logic for all three table types (songs, shows, setlists)
- Implemented warning-only validation with detailed logging
- Added `--skip-validation` command-line flag for advanced users
- Consistent warning format across all tables

### 3. GitHub Actions Workflow (`.github/workflows/daily-pipeline.yml`)

**Removed `--skip-validation` flags**:
- Updated comments to reflect warning-only validation approach
- Removed `--skip-validation` from all collection script invocations
- Collections now run with validation enabled by default (but permissive)
- Validation warnings will appear in GitHub Actions logs for monitoring

**Benefits**:
- Data quality issues are visible in logs without blocking inserts
- Collections are more resilient to schema evolution
- Easier to diagnose data issues from GitHub Actions logs

## Testing Recommendations

Before deploying to production:

1. **Test Each Band Collection Locally**:
   ```bash
   uv run python scripts/run_goose_collection.py
   uv run python scripts/run_phish_collection.py
   uv run python scripts/run_wsp_collection.py
   ```
   - Verify that validation warnings appear in console output
   - Confirm data is still inserted into Supabase tables
   - Check for any unexpected errors

2. **Test GitHub Actions Workflow**:
   - Trigger the workflow manually using `workflow_dispatch`
   - Choose a specific band to test first (e.g., `goose`)
   - Review logs to ensure validation warnings are visible
   - Verify that the pipeline completes successfully

3. **Data Quality Verification**:
   - After running collections, use the diagnostic script:
     ```bash
     uv run python scripts/diagnose_band_data.py --band goose
     uv run python scripts/diagnose_band_data.py --band phish
     uv run python scripts/diagnose_band_data.py --band wsp
     ```
   - Check for orphaned shows, missing setlists, etc.

## Benefits

1. **Robustness**: Collections won't fail due to minor schema mismatches
2. **Visibility**: Validation issues are logged but don't block progress
3. **Maintainability**: Consistent validation approach across all bands
4. **Debugging**: Clear, detailed warning messages make issues easy to diagnose
5. **Flexibility**: `--skip-validation` flag still available for advanced use cases

## Future Improvements

1. Consider adding validation metrics to a monitoring dashboard
2. Set up alerts for repeated validation warnings (might indicate schema drift)
3. Implement automated schema migration detection
4. Add validation summary to GitHub Actions pipeline summary

## Command Reference

### Collection with Warning-Only Validation (Default)
```bash
uv run python scripts/run_goose_collection.py
uv run python scripts/run_phish_collection.py
uv run python scripts/run_wsp_collection.py
```

### Collection with Validation Completely Disabled
```bash
uv run python scripts/run_goose_collection.py --skip-validation
uv run python scripts/run_phish_collection.py --skip-validation
uv run python scripts/run_wsp_collection.py --skip-validation
```

### Full Pipeline (All Bands)
```bash
uv run python scripts/run_optimized_pipeline.py --band all
```

## Related Files

- `src/jambandnerd/db/validation.py` - Core validation logic
- `scripts/run_goose_collection.py` - Goose collection with warning-only validation
- `scripts/run_phish_collection.py` - Phish collection with warning-only validation
- `scripts/run_wsp_collection.py` - WSP collection with warning-only validation
- `.github/workflows/daily-pipeline.yml` - Automated daily pipeline
- `scripts/diagnose_band_data.py` - Data quality diagnostic tool
