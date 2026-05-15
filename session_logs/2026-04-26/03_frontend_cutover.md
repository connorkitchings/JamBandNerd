# Frontend Cutover — single-model-per-band

## Goal

Migrate the website from legacy multi-model tables (`predictions`, `accuracy_per_show`) to the new single-model `setlist_*` tables. Remove all multi-model UI surface: `/compare`, `/replay`, `/explorer` routes, model picker, model display names, and model-specific branching in components.

## Constraints

- No backend changes (Phase A is complete).
- Model names are not public-facing. `model_version` stays on the data row for internal iteration only.
- `/replay`, `/compare`, `/explorer` are deleted entirely — no redirects.
- `song-board.tsx` adopts Deal-style columns universally (Recent Plays, Probability).

## Commands Run

```bash
# TypeScript
cd apps/web && npx tsc --noEmit          # 0 errors in src/

# Lint
cd apps/web && npx eslint . --max-warnings=0   # clean

# Build
cd apps/web && npx next build                   # succeeds, no /compare /replay /explorer routes

# Unit tests
node --test apps/web/tests/unit/*.test.ts       # 14/15 pass
# (1 pre-existing failure in song-board.test.ts due to @/ path alias)

# Backend sanity
npm run verify:python                           # 341 passed, 6 skipped (unchanged)
npm run verify:docs                             # MkDocs strict build passed
```

## Files Changed

### Data layer
- `apps/web/src/lib/data/types.ts` — dropped `ModelSlug`, `ExplorerSnapshot`, `ReplaySnapshot`, `ReplayShowOption`, `ckplusScore`; added `weightedPrecisionScore`, renamed accuracy fields
- `apps/web/src/lib/data/parsers.ts` — dropped `ckplusScore` parsing from both normalize functions
- `apps/web/src/lib/data/predictions.ts` — rewrote to query `setlist_predictions`; deleted `getCurrentModelVersion`, `resolveReplayModels`, `getExplorerSnapshot`; dropped all model parameters
- `apps/web/src/lib/data/accuracy.ts` — migrated to `setlist_accuracy` table; dropped model parameter
- `apps/web/src/lib/live-updates.ts` — dropped `model` from update scope
- `apps/web/src/lib/data/replay.ts` — **deleted**
- `apps/web/src/lib/data.ts` — dropped re-exports of deleted items

### Config
- `apps/web/src/lib/config.ts` — deleted `ModelVisibility`, `MODEL_CONFIG`, `ALL_MODELS`, `ACTIVE_MODELS`, `ModelSlug`, `normalizeModel`

### Deleted components
- `apps/web/src/components/compare-metric-select.tsx`
- `apps/web/src/components/replay-show-select.tsx`
- `apps/web/src/lib/model-agreement.ts`

### Deleted routes
- `apps/web/src/app/compare/page.tsx`
- `apps/web/src/app/replay/page.tsx`
- `apps/web/src/app/explorer/page.tsx`

### Rewritten components
- `song-board.tsx` — dropped `modelSlug` prop, `isDeal` branching, `secondarySongs`, `ModelAgreeIcon`; Deal-style columns now universal
- `dashboard-side-nav.tsx` — dropped model prop/column; band-only nav
- `live-tracker.tsx` — dropped model prop; subscribes to `setlist_prediction_songs`
- `filter-links.tsx` — dropped model prop/model selector
- `accuracy-table.tsx` — removed `/replay` link cell, updated field names
- `recall-chart.tsx` — updated `k10Recall` → `recall10` etc.
- `dashboard-analysis.tsx` — updated `k10Recall` → `recall10`

### Rewritten pages
- `page.tsx` (home) — dropped `ACTIVE_MODELS`, model redirect, "Top Picks (Notebook)" copy, "Prediction Models" stat
- `predictions/page.tsx` — dropped model from searchParams, metadata, data calls, side nav, live tracker, song board
- `performance/page.tsx` — dropped model handling, `buildReplayHref`, all `/replay` links
- `last-show/page.tsx` — dropped `"notebook"` hardcoding, `/replay` links, `&model=notebook` hrefs
- `about/page.tsx` — rewrote "How the Models Work" → "How Predictions Work"; removed MODEL_CONFIG references; updated FAQ
- `data-use/page.tsx` — rewrote model-naming paragraph generically
- `preview/tables/page.tsx` — trimmed `ckplusScore`, updated accuracy field names

### Navigation
- `apps/web/src/lib/navigation.ts` — removed `/compare`, `/replay`, `/explorer` nav items

### Utility
- `apps/web/src/lib/format-predictions-text.ts` — dropped `modelDisplayName` from options type

### Tests
- `tests/unit/model-agreement.test.ts` — **deleted**
- `tests/unit/format-predictions-text.test.ts` — removed `ckplusScore`, `modelDisplayName`; updated share URLs
- `tests/unit/song-board.test.ts` — removed `ckplusScore`; fixed `"unlikely"` → `"possible"`; added `recentPlays50`
- `tests/unit/live-updates.test.ts` — removed `model` from scope; dropped model_slug matching tests
- `tests/smoke/public-shell.spec.ts` — removed `/compare`, `/replay` visits; removed `&model=notebook` redirect
- `tests/smoke/mobile-flows.spec.ts` — removed replay cards, compare stacks, model combobox assertions

## Validation Status

- TypeScript: 0 errors in `src/`
- ESLint: 0 warnings
- Next.js build: passes
- Unit tests: 14/15 (1 pre-existing `@/` path alias failure)
- Python: 341 passed, 6 skipped (unchanged)
- Docs: MkDocs strict build passes
- **Not run**: `npm run verify:web` (Playwright smokes require hosted target), `npm run verify:clean`

## Open Items

- `song-board.test.ts` pre-existing failure: `@/lib/config` path alias not resolvable by `node --test` runner
- Do not merge to `main` until Goose Supabase dry-run populates `setlist_*` tables
- `dashboard-analysis.tsx` has a `modelLabel` string prop — unused component, not imported anywhere
- Manual smoke needed: verify Deal-style columns render for all five bands when `setlist_*` tables are populated

## Next Step

Run Goose Supabase dry-runs once env vars are available, then manual smoke test before merge to `main`.
