# Session Log: Simplify Home and Restore Replay

Date: 2026-05-15

## Summary

- Responded to product feedback that the band-first homepage was too cluttered.
- Simplified the homepage to a compact hero, primary links, supported bands, and three high-level product areas.
- Restored `/replay` as a public route while keeping `/compare` removed.
- Added Replay back to desktop and mobile navigation.
- Updated prediction hero metrics to show both Precision and Recall at Top 10, Top 25, and Top 50.
- Kept existing query-string compatibility:
  - `/predictions?band=...`
  - `/performance?band=...`
  - `/last-show?band=...`
  - `/replay?band=...&date=...`

## Goal

- Correct the public website direction after the band-first homepage shipped too much dashboard density.
- Preserve the requested removal of Compare while restoring Replay.
- Make prediction-page metrics clearer now that the retained accuracy table stores both precision and recall.

## Constraints

- Keep existing query-string URLs stable.
- Keep `/compare` unavailable.
- Do not reintroduce public model pickers or model comparison UX.
- Continue using the current single-model `setlist_*` read surface.

## Replay Behavior

- Replay now shows one retained single-model board for a completed show.
- The route uses current single-model reads:
  - `bands`
  - `setlist_results`
  - `setlist_accuracy`
  - raw band show/setlist tables for actual setlists
- Replay highlights prediction hits against the actual setlist.
- Compare and Explorer remain unavailable.

## Metrics Behavior

- Prediction pages no longer label recall-only values as generic accuracy.
- Each Top-K card now stacks:
  - Precision: share of these picks that were played.
  - Recall: share of the setlist found in the Top-K group.
- Values come from averaged `p10/p25/p50` and `recall_10/recall_25/recall_50` rows in `setlist_accuracy`.

## Files Changed

- `apps/web/src/app/page.tsx`
- `apps/web/src/app/replay/page.tsx`
- `apps/web/src/app/predictions/page.tsx`
- `apps/web/src/app/performance/page.tsx`
- `apps/web/src/app/last-show/page.tsx`
- `apps/web/src/components/prediction-hero.tsx`
- `apps/web/src/components/replay-show-select.tsx`
- `apps/web/src/lib/navigation.ts`
- `apps/web/tests/smoke/mobile-flows.spec.ts`
- `apps/web/tests/smoke/public-shell.spec.ts`
- `apps/web/tests/unit/navigation.test.ts`

## Verification

- `npm run verify:web` passed.

## Commands Run

- `npm run verify:web`

## Next Step

- Preview `codex/simplify-home-restore-replay` locally, then push/open a PR to `dev` if the simplified homepage, restored Replay route, and precision/recall cards look right.
