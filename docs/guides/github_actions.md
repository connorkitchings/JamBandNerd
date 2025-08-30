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
