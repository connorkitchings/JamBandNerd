# 2026-03-21 Session Log 08

## Goal
Fix the new `Website Quality` pull-request failure after converting the workflow to
run real Playwright smoke tests.

## Root Cause
- Pull-request workflows do not have Supabase secrets available.
- The smoke test expected live route headings on `/performance`, `/explorer`,
  `/compare`, and `/predictions`, but CI correctly rendered the explicit
  `Supabase environment required` fallback state on those routes.

## Files Changed
- `apps/web/tests/smoke/public-shell.spec.ts`

## What Changed
- Added a smoke-test helper that accepts either the normal route heading or the
  explicit missing-env fallback heading.
- Kept the smoke suite strict about route rendering and navigation while making
  it compatible with the no-secrets PR environment used by GitHub Actions.

## Validation
- `npm run lint:web`: passed
- `npm run build:web`: passed
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npm run test:web:smoke`:
  passed outside the sandbox

## Next Step
Push the fix to PR `#8`, rerun `Website Quality`, and merge once GitHub and
Vercel checks are green.
