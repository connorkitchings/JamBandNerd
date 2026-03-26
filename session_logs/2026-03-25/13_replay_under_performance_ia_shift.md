# Session Log: 2026-03-25 - Replay Under Performance IA Shift

## Goal

Move historical prediction replay under the performance experience instead of
presenting it as a peer deep-dive view next to compare.

## Constraints

- Keep replay on the existing detail route for now
- Make `Compare` standalone
- Make `Performance` the owner/gateway for replay
- Preserve existing route/query behavior where practical

## Commands run

- `npm run lint:web`
- `npm run build:web`

## Files changed

- `apps/web/src/app/_venues/page.tsx`
- `apps/web/src/app/compare/page.tsx`
- `apps/web/src/app/explorer/page.tsx`
- `apps/web/src/app/last-show/page.tsx`
- `apps/web/src/app/performance/page.tsx`
- `apps/web/src/components/accuracy-table.tsx`
- `apps/web/src/components/dashboard-side-nav.tsx`
- `apps/web/src/lib/navigation.ts`

## Validation status

- `npm run lint:web`: passed
- `npm run build:web`: passed

## Notes

- `/compare` now uses only the shared band selector at the top
- `/explorer` is framed as `Prediction Replay` / `Performance review`, not a peer top-level deep-dive view
- desktop/mobile nav now treat `/explorer` as part of the performance surface
- performance now links into replay from:
  - latest scored show
  - best night
  - recent mobile cards
  - desktop/mobile raw ledger table
- supporting copy was updated in `last-show` and `_venues` so links point to replay rather than “Historical Analysis”
