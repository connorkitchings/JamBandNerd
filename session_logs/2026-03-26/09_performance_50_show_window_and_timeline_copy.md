# Session 35: Performance 50 Show Window And Timeline Copy

**Date:** 2026-03-26  
**Goal:** Expand the Performance page to 50 shows and simplify the timeline section title/copy.

## Constraints
- Use a 50-show accuracy window instead of 25
- Remove the `Top-X accuracy over time` eyebrow from the timeline card
- Rename the timeline card to the active model name plus `Accuracy Over Time`

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/performance/page.tsx` - Increased the recent accuracy fetch to 50 shows and retitled the timeline section

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
If needed, trace the two missing Goose compare nights to confirm whether one model lacks scored rows for those dates.
