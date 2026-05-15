# Session Log: Band-First Site Structure

Date: 2026-05-15

## Summary

- Merged the focused retained-window/public-comparison PR into `dev` after CI passed.
- Created `codex/band-first-site-structure` from updated `dev`.
- Reworked the homepage from a teaser/marketing surface into an active-band overview dashboard.
- Kept the compatibility route contract unchanged:
  - `/`
  - `/predictions?band=...`
  - `/performance?band=...`
  - `/last-show?band=...`
- Preserved 404 behavior for `/compare`, `/replay`, and `/explorer`.

## Website Changes

- Homepage now reads the active `bands` registry and builds per-band cards from:
  - `setlist_predictions`
  - `setlist_results`
  - `setlist_accuracy`
- Homepage surfaces:
  - active band count
  - ready board count
  - count of bands with exactly 50 scored rows available to the page
  - next target show context
  - top board picks
  - last-50 Top 25 average
  - links into Predictions, Performance, and Last Show with `?band=` retained
- Performance copy now explicitly describes the active per-band model and the retained last-50 scored-show ledger.
- Last Show copy now frames the page as prediction-vs-actual overlap, not public model comparison.

## Verification

- `npm run verify:web` passed.

## Notes

- Eggy remains hidden unless it is active in the `bands` table and has validated `setlist_*` rows.
- No public model picker, model slug surface, comparison route, replay route, explorer route, or band-first path routing was added.
