# 2026-03-21 Session Log 07

## Goal
Implement the remaining MVP hardening work by turning website smoke checks into a
real GitHub Actions gate, verifying current production data freshness, and
packaging the branch for PR review.

## Constraints
- Keep the website verification path aligned with the existing Playwright smoke
  suite.
- Do not broaden the PR into unrelated frontend or pipeline refactors.
- Preserve `main` as the production branch and the Vercel deployment target.

## Commands Run
- `npm run lint:web`
- `npm run build:web`
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npm run test:web:smoke`
- `gh run list --workflow=daily-pipeline.yml --limit 5`
- `uv run python scripts/validate_prediction_tables.py`
- `uv run python scripts/audit_raw_data.py --band all`

## Files Changed
- `.github/workflows/web-quality.yml`
- `docs/operations/website_delivery.md`

## What Changed
- Updated `Website Quality` to install Playwright Chromium and run the actual
  smoke suite instead of `npm run test:web:smoke:list`.
- Updated the website delivery doc so the documented GitHub verification flow
  matches the workflow behavior.

## Validation
- `npm run lint:web`: passed
- `npm run build:web`: passed
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npm run test:web:smoke`:
  failed in the sandbox because Chromium aborted on launch with `SIGABRT`, then
  passed outside the sandbox
- `gh run list --workflow=daily-pipeline.yml --limit 5`: latest scheduled run on
  `main` succeeded (`23386620613`)
- `uv run python scripts/validate_prediction_tables.py`: passed for Notebook and
  CK+ across all supported bands with fresh `predicted_at` timestamps
- `uv run python scripts/audit_raw_data.py --band all`: all bands clean; WSP has
  one warning-only upstream-missing setlist for `2026-03-20` (`show_id=22455`)

## Next Step
Push this branch, open the PR to `main`, and let the updated `Website Quality`
workflow and Vercel preview complete before merging.
