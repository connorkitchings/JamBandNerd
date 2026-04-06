# Session 29: Replay Table Simplification And Encore Label Normalization

**Date:** 2026-03-26  
**Goal:** Simplify the Replay page into a single rank-aligned model table and normalize actual setlist display so set `99` renders as `E`.

## Constraints
- Keep Replay as a side-by-side Notebook vs CK+ review surface
- Remove lower-page board detail without losing played/missed clarity
- Apply the encore label change everywhere the website renders actual setlist order

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/replay/page.tsx` - Replaced dual detailed song boards with one rank-aligned comparison table
- `apps/web/src/components/setlist-table.tsx` - Uses shared set-label formatter for actual setlist display
- `apps/web/src/lib/format.ts` - Added `formatSetLabel()` with `99 -> E` display mapping

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
Continue the page-by-page once-over on the next web route that needs simplification or display cleanup.
