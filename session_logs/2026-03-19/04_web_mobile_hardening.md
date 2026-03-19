# 2026-03-19 Session Log 04

## Goal

Carry over the useful PanicStats web/mobile lessons into JamBandNerd without importing its SPA architecture.

## Constraints

- Keep JamBandNerd server-first in Next.js.
- Avoid viewport hooks unless layout cannot be solved with CSS or route metadata.
- Keep dense data modules scroll-safe on mobile.
- Add verification for the public shell and mobile behavior.

## Commands Run

- `git status --short`
- `sed -n ...` on `.agent/AGENTS.md`, the Vercel React best-practices skill, and the relevant `apps/web` files
- `npm_config_cache=/Users/connorkitchings/.cache/npm npm install --workspace @jambandnerd/web --save-dev @playwright/test`
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npx playwright install chromium`
- `npm run lint:web`
- `npm run build:web`
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npm run test:web:smoke`
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npx playwright test --list`

## Files Changed Or Artifacts Produced

- Added shared route metadata and route classification for desktop/mobile shell behavior.
- Added safe-area-aware mobile nav and content padding.
- Added a shared responsive table frame and applied it to prediction, accuracy, and setlist tables.
- Added an internal `/preview/tables` route for responsive table QA without live Supabase data.
- Added Playwright smoke coverage for desktop shell, mobile nav ordering, detail back affordance, and mobile table scrolling.
- Updated website delivery docs and web README with the new defaults and commands.

## Validation Status

- `npm run lint:web`: passed
- `npm run build:web`: passed
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npx playwright test --list`: passed
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npm run test:web:smoke`: failed in this sandbox because Chromium aborted at launch with macOS Mach-port permission errors before any test code executed

## Next Step

Extend the same shell and dense-data rules to future song/show detail routes as JamBandNerd adds them.
