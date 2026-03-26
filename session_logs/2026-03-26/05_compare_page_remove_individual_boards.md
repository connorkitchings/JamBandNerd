# Session 31: Compare Page Remove Individual Boards

**Date:** 2026-03-26  
**Goal:** Remove the individual model prediction boards from Compare now that Replay owns show-level board review.

## Constraints
- Keep Compare focused on head-to-head summaries and historical record
- Do not rework Replay in the same pass

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/compare/page.tsx` - Removed the two bottom per-model board sections and cleaned unused board state/imports

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
Continue the web once-over on the next route that still overlaps with Replay or feels too dense.
