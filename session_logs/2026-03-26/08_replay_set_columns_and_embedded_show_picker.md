# Session 34: Replay Set Columns And Embedded Show Picker

**Date:** 2026-03-26  
**Goal:** Rework the Replay actual setlist into set-based columns and move the show selector into the Actual Setlist section.

## Constraints
- Render one column per set for 1, 2, or 3 set shows
- Render the encore underneath the main set columns
- Remove the standalone Select Show card
- Keep Replay server-rendered apart from the existing dropdown client component

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/replay/page.tsx` - Replaced the standalone Select Show card with an embedded dropdown inside Actual Setlist and removed the date eyebrow from that section
- `apps/web/src/components/replay-show-select.tsx` - Added an optional small label above the dropdown
- `apps/web/src/components/setlist-columns.tsx` - Added the new per-set column layout with a separate encore section

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
Continue the web app once-over on the next page or keep refining Replay presentation details.
