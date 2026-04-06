# Session Log: 2026-03-25 - Mobile Density Remediation After Visual QA

## Goal

Fix the mobile-specific readability and hierarchy issues found during browser-based visual QA, especially on dense product routes like Compare and Performance, without undoing the broader editorial web refresh.

## Constraints

- Preserve the current website visual direction and desktop quality
- Keep all route/query contracts unchanged
- Focus on mobile compaction and summary-first readability rather than another large redesign
- Maintain the website-first flow before any mobile-app work begins

## Commands run

- `npm run lint:web`
- `npm run build:web`
- `npm run start --workspace @jambandnerd/web -- --hostname 127.0.0.1 --port 3101`
- `npx playwright screenshot --device="Pixel 7" --full-page --wait-for-timeout 1500 http://127.0.0.1:3101/predictions /tmp/jbn-predictions-mobile-v2.png`
- `npx playwright screenshot --device="Pixel 7" --full-page --wait-for-timeout 1500 http://127.0.0.1:3101/performance /tmp/jbn-performance-mobile-v2.png`
- `npx playwright screenshot --device="Pixel 7" --full-page --wait-for-timeout 1500 http://127.0.0.1:3101/compare /tmp/jbn-compare-mobile-v2.png`
- `npx playwright screenshot --device="Pixel 7" --full-page --wait-for-timeout 1500 http://127.0.0.1:3101/last-show /tmp/jbn-last-show-mobile-v2.png`

## Files changed

- `apps/web/src/components/filter-links.tsx`
- `apps/web/src/components/page-hero.tsx`
- `apps/web/src/app/performance/page.tsx`
- `apps/web/src/app/compare/page.tsx`
- `apps/web/src/app/last-show/page.tsx`

## Validation status

- `npm run lint:web`: passed
- `npm run build:web`: passed
- Follow-up browser QA:
  - mobile filter stack is more compact across product pages
  - `performance` now exposes readable summary cards before the raw ledger
  - `compare` now exposes readable matchup summaries before the dense ledger
  - `last-show` benefits from the same shell compaction and is easier to scan near the top

## Next step

Do one final broader browser QA sweep across remaining product routes (`/explorer`, `/venues`, desktop compare/performance) and then decide whether the web version is complete enough to move into mobile app work.
