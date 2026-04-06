# Session 32: Compare Historical Only Focus

**Date:** 2026-03-26  
**Goal:** Remove snapshot-sync and latest-board framing from Compare so the page focuses only on model performance over time.

## Constraints
- Keep Compare centered on historical model-vs-model performance
- Remove any remaining latest-snapshot or current-board comparisons
- Ensure the head-to-head label reads `Last 50 shows evaluated`

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/compare/page.tsx` - Removed latest snapshot dependencies, removed overlap/divergence sections, replaced snapshot-sync hero copy with historical window framing, and fixed the head-to-head label to 50 shows

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
Continue the web once-over on the next page that still needs tighter focus or reduced density.
