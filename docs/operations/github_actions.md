# GitHub Actions - Daily Pipeline

This repository runs a daily data pipeline via GitHub Actions.

## Triggers

- Scheduled: Daily at 19:00 UTC (3:00 PM ET during DST)
- Manual: `workflow_dispatch` with:
  - `band`: `all` or a single band from the dynamically discovered list
  - `skip_accuracy`: skip backtesting/aggregate accuracy for a faster run

## Overview

- Collect raw data for selected band(s)
- Generate predictions for Notebook and CK+
- Optionally run backtests + aggregate accuracy
- Run freshness checks and write a run summary

## Notes

- Secrets required: `SUPABASE_URL`, `SUPABASE_KEY`; `PHISH_API_KEY` is required only for the Phish collector.
- For WSP, the workflow installs Playwright (Firefox) to improve CI scraping reliability.
- The pipeline validates prediction table freshness (`scripts/validate_prediction_tables.py`) after generation, using the latest written prediction row by `predicted_at`.
- Accuracy backtesting excludes shows with 5 or fewer unique songs.

## Optional Notifications

If `DISCORD_WEBHOOK_URL` is set in GitHub Secrets, the workflow posts a success/failure message with a link to the run.

## Data Validation

As of 2025-10-04, all collection scripts use **warning-only validation**:

- **Type mismatches** are logged as warnings but don't block data inserts
- **Missing required columns** and **nullable violations** still cause validation failure
- Validation warnings appear in GitHub Actions logs for monitoring
- No `--skip-validation` flags needed in the workflow

For more details, see:
- `VALIDATION_IMPROVEMENTS.md` - Complete documentation
- `TEST_REPORT_VALIDATION.md` - Testing and verification results
