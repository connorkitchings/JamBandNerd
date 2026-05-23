# Session Log: UM Replay & Smoke Fixes

Date: 2026-05-23

## Goal

- Diagnose why Umphrey's McGee (UM) setlists were not appearing on the Replay page.
- Remove the mobile back button from `SiteHeader` as requested and update Playwright smoke tests to match.
- Run complete repository quality gates (Python verify, docs build, web build, eslint, unit tests, and Playwright smoke tests) to ensure readiness.

## Constraints

- Avoid working directly on `main` (stay on `dev`).
- Preserve the anti-leakage `reference_date` rules.
- Maintain the unified single-model-per-band structure.

## Commands Run

```bash
uv run python scripts/get_all_bands.py
uv run python scripts/diagnose_band_data.py --band um --verbose
npm run test:web:unit
npm run verify:python
npm run verify:docs
npm run lint:web
npm run build:web
npm run test:web:smoke
```

## Files And Artifacts

- `apps/web/src/lib/data/shows.ts`
- `apps/web/src/components/site-header.tsx`
- `apps/web/tests/smoke/mobile-flows.spec.ts`
- `apps/web/tests/smoke/public-shell.spec.ts`
- `docs/operations/mobile_verification.md`

## Validation

- **Python verify (`verify:python`)**: Passed all 583 tests (including live band smoke tests for Goose, Phish, WSP, Billy Strings, and UM).
- **Docs verify (`verify:docs`)**: Built the documentation cleanly with no errors.
- **Web unit tests (`test:web:unit`)**: Passed all 30 tests.
- **Web linting (`lint:web`)**: ESLint passed cleanly.
- **Web build (`build:web`)**: Compiled successfully.
- **Web Playwright smoke tests (`test:web:smoke`)**: All 16 run tests passed successfully.

## Next Step

- Push the changes to the `dev` branch and open the PR to `main`.
