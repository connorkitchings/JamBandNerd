# Session 37: Frontend Hardening Pass

**Date:** 2026-03-26  
**Goal:** Tighten frontend maintainability and runtime behavior without changing the current UX.

## Scope
- Remove unused global search code that was no longer mounted anywhere in `apps/web`
- Narrow realtime subscriptions on `/predictions` so they only run for the active live show
- Extract and test small helper modules for song-board grouping and live-update scoping
- Split the `song-board` rendering path into smaller internal units

## Files Changed
| File | Action |
|------|--------|
| `apps/web/src/app/predictions/page.tsx` | Gated `LiveTracker` to live-show state and passed scoped identifiers |
| `apps/web/src/components/live-tracker.tsx` | Narrowed realtime subscription to relevant band updates and filtered refreshes by band/model/date |
| `apps/web/src/components/song-board.tsx` | Extracted smaller internal render sections and reused helper logic |
| `apps/web/src/lib/song-board.ts` | Created shared normalization and tier-grouping helpers |
| `apps/web/src/lib/live-updates.ts` | Created payload-scope matcher for realtime updates |
| `apps/web/src/lib/data.ts` | Removed unused `getGlobalSearchData` |
| `apps/web/src/components/global-search.tsx` | Deleted unused component |
| `apps/web/tests/unit/song-board.test.ts` | Added helper coverage |
| `apps/web/tests/unit/live-updates.test.ts` | Added realtime scope-matcher coverage |

## Validation
- `npm run lint:web`: passed
- `npm run build:web`: passed

## Notes
- Direct `node --test` execution for the new web unit tests is not wired cleanly yet because the app source uses `@/` path aliases. The tests are kept in place for the existing web test surface, but standalone Node execution needs alias-aware test tooling if we want to run them outside the app toolchain.
- I intentionally did not do the larger `lib/data.ts` split in this pass because the web tree was already heavily in motion and a broad extraction would have created unnecessary merge risk.
