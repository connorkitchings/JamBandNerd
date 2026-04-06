# Session 30: Replay Dropdown And Table Status Simplification

**Date:** 2026-03-26  
**Goal:** Replace the Replay show button rail with a dropdown selector, move the actual setlist ahead of the compare table, and simplify the compare-table played/missed status display.

## Constraints
- Keep the Replay hero intact
- Use a native auto-navigating dropdown rather than a custom combobox
- Keep Replay server-rendered apart from the selector interaction

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/replay/page.tsx` - Reordered sections and replaced the show rail with a single selector section
- `apps/web/src/components/replay-show-select.tsx` - New client-side native show selector with immediate navigation

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Next Step
Continue the page-by-page web cleanup pass on the next route.
