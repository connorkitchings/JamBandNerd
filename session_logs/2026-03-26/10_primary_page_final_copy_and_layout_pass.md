# Session 36: Primary Page Final Copy And Layout Pass

**Date:** 2026-03-26  
**Goal:** Make final copy and layout cleanups across Home, Predictions, Performance, Compare, and Replay.

## Constraints
- Keep the changes focused on page hierarchy, labels, and summary sections
- Preserve the current route structure and data contracts
- Re-run web validation after the full multi-page sweep

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/page.tsx` - Removed the extra workflow/artist-count eyebrows and renamed the artist section
- `apps/web/src/app/predictions/page.tsx` - Switched prediction metric cards to a 50-show window
- `apps/web/src/app/performance/page.tsx` - Removed the extra detail cards, tightened the latest-show summary, restored `Recent Show Accuracy`, and kept the 50-show window
- `apps/web/src/components/k-toggle.tsx` - Moved `All` to the front of the chart toggle
- `apps/web/src/components/recall-chart.tsx` - Restored the auto-fit y-axis
- `apps/web/src/app/compare/page.tsx` - Simplified the hero and removed the comparison window panel
- `apps/web/src/app/replay/page.tsx` - Simplified the hero copy and renamed the comparison section to `Notebook vs CK+`

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
Continue the final once-over on any remaining primary page details that still feel dense or redundant.
