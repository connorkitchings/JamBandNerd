# Session 33: Compare Metric Selector And Average Row

**Date:** 2026-03-26  
**Goal:** Add an average row to the Compare head-to-head table, keep all 50 evaluated shows listed, and let the user switch the comparison metric between Top 10, Top 25, and Top 50.

## Constraints
- Keep the evaluation window fixed at 50 shows
- Add the selector at the top right of the Head-to-Head Record card
- Leave `Average` under the date column and the venue cell blank

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/compare/page.tsx` - Added the average ledger row, kept the full 50-show ledger visible, and made the compare cards/tables switch between Top 10, Top 25, and Top 50 metrics via query param
- `apps/web/src/components/compare-metric-select.tsx` - Added the client dropdown for metric selection
- `apps/web/src/components/section-card.tsx` - Added a header accessory slot so cards can place controls in the top-right corner

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
Continue the web app once-over on the next page that still has dense or redundant comparison UI.
