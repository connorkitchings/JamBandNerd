# Session 28: Route Contract Cleanup And Mobile Touch Baseline

**Date:** 2026-03-26  
**Goal:** Implement the March 25 cleanup plan by fixing route/docs drift and tightening the shared mobile touch/layout baseline.

## Constraints
- Keep `/replay` as the canonical historical review surface
- Make `/venues` the public venue analytics contract
- Keep Streamlit out of the active public path while preserving internal/debug wording
- Focus mobile work on layout/touch behavior rather than render/data optimization

## Commands Run
```bash
git checkout -b fix-mobile-route-doc-drift
npm run lint:web
npm run build:web
npm run test:web:smoke
npm run start --workspace @jambandnerd/web -- --hostname 127.0.0.1 --port 3201
curl -I -s http://127.0.0.1:3201/venues
curl -I -s 'http://127.0.0.1:3201/_venues?band=goose'
curl -I -s http://127.0.0.1:3201/preview/tables
curl -I -s 'http://127.0.0.1:3201/explorer?band=goose&date=2026-03-20'
```

## Files Changed

### Web routes and mobile UX
- `apps/web/src/app/venues/venue-analytics-page.tsx` - Canonical venue analytics page content
- `apps/web/src/app/venues/page.tsx` - Public `/venues` route
- `apps/web/src/app/_venues/page.tsx` - Legacy path cleanup
- `apps/web/src/app/globals.css` - Shared horizontal-scroll helpers
- `apps/web/src/components/responsive-table.tsx` - Shared scroll surface usage
- `apps/web/src/components/dashboard-side-nav.tsx` - Touch-safe selector links
- `apps/web/src/components/mobile-bottom-nav.tsx` - Larger thumb targets
- `apps/web/src/components/k-toggle.tsx` - Touch-safe toggle buttons
- `apps/web/src/app/replay/page.tsx` - Shared mobile pill rail
- `apps/web/src/app/performance/page.tsx` - Touch-safe replay CTAs
- `apps/web/src/app/predictions/page.tsx` - Tighter mobile padding

### Docs and specs
- `docs/contributor/developer_guide/architecture.md`
- `docs/operations/frontend_strategy.md`
- `docs/operations/mobile_verification.md`
- `docs/overview/project/prd.md`
- `docs/reference/specifications/cli.md`
- `docs/reference/specifications/technical_overview.md`

### Pipeline consistency
- `scripts/save_aggregate_accuracy.py` - Dynamic active-band choices

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed
- Local route checks:
  - `/venues`: `200 OK`
  - `/preview/tables`: `200 OK`
  - `/explorer?band=goose&date=2026-03-20`: `307` redirect to `/replay?...`
- `npm run test:web:smoke`: blocked by local Playwright Chromium launch failure (`SIGABRT`) before test execution

## Next Step
Continue the mobile optimization track with a deeper pass on dense route readability and touch ergonomics now that the route and documentation baseline is consistent.
