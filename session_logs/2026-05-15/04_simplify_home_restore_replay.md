# Session Log: Simplify Home and Restore Replay

Date: 2026-05-15

## Summary

- Responded to product feedback that the band-first homepage was too cluttered.
- Simplified the homepage to a compact hero, primary links, supported bands, and three high-level product areas.
- Restored `/replay` as a public route while keeping `/compare` removed.
- Added Replay back to desktop and mobile navigation.
- Kept existing query-string compatibility:
  - `/predictions?band=...`
  - `/performance?band=...`
  - `/last-show?band=...`
  - `/replay?band=...&date=...`

## Replay Behavior

- Replay now shows one retained single-model board for a completed show.
- The route uses current single-model reads:
  - `bands`
  - `setlist_results`
  - `setlist_accuracy`
  - raw band show/setlist tables for actual setlists
- Replay highlights prediction hits against the actual setlist.
- Compare and Explorer remain unavailable.

## Verification

- `npm run verify:web` passed.
