# GitHub Actions - Daily Pipeline

This repository runs a daily data pipeline via GitHub Actions.

## Triggers

- Scheduled: Daily at 19:00 UTC (3:00 PM ET during DST)
- Manual: `workflow_dispatch` with band selection
  - Options: `all`, `goose`, `phish`, `wsp`
  - Optional: `use_optimized_pipeline` (single-script) or standard multi-step jobs

## Overview

- Collect data for selected bands
- Generate predictions for Notebook and CK+
- Calculate accuracy metrics and upsert to Supabase

## Notes

- Secrets required: `SUPABASE_URL`, `SUPABASE_KEY`, `PHISH_API_KEY` (for Phish)
- The optimized pipeline reuses loaded data and calculates accuracy over the last 100 valid shows per band.
- Accuracy backtesting excludes shows with 5 or fewer unique songs.

## Data Validation

As of 2025-10-04, all collection scripts use **warning-only validation**:

- **Type mismatches** are logged as warnings but don't block data inserts
- **Missing required columns** and **nullable violations** still cause validation failure
- Validation warnings appear in GitHub Actions logs for monitoring
- No `--skip-validation` flags needed in the workflow

For more details, see:
- `VALIDATION_IMPROVEMENTS.md` - Complete documentation
- `TEST_REPORT_VALIDATION.md` - Testing and verification results
