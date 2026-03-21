# 2026-03-21 Session Log 05

## Goal
Design and implement the architecture for: (A) a dynamic band platform backed by Supabase, and (B) a documented model pluggability workflow.

## Decisions Made
- **Band registry**: `bands` Supabase table — single write point, website reads dynamically. New band onboarding = collector + insert row.
- **Model config**: Keep `MODEL_CONFIG` in `config.ts` as a code change (not Supabase-backed).
- **Band-model combos**: All combinations valid by default (no per-model band allowlist).
- **Invalid band slug UX**: Show "Band not found" error page (not silent fallback to default).
- **Band seed dates**: `created_at = now()` for all existing bands.

## What Changed

### Migration
- `supabase/migrations/20260321_create_bands_registry.sql`: `bands` table with `slug` (PK), `display_name`, `shows_table`, `id_column`, `is_active`, `created_at`. Seeded with all 6 existing bands with `on conflict` upsert.

### Website Data Layer (`apps/web/src/lib/data.ts`)
- Added `BandEntry` type and `getBands()` cached server function — reads active bands from `bands` table.
- Added `bandEntryBySlug()` and `isValidBandSlug()` helpers.
- `getPredictionDates` now prefers `prediction_songs` for date enumeration, falls back to legacy `predictions_{model}` table.
- `getGlobalSearchData` fetches bands from Supabase instead of hardcoded `BAND_CONFIG` keys.

### Website Pages
- All 5 band-aware pages (`/`, `/explorer`, `/compare`, `/last-show`, `/performance`) now:
  - Fetch bands from `getBands()` in parallel with data fetchers
  - Validate the band slug against the fetched list
  - Render a "Band not found" `DataState` error for invalid slugs
  - Pass `bands: BandEntry[]` to `FilterLinks`
- `DashboardSideNav` now accepts `bands: BandEntry[]` prop and iterates it instead of `ACTIVE_BANDS`.
- `FilterLinks` now accepts `bands: BandEntry[]` prop.
- `about/page.tsx` is async and fetches bands dynamically for the supported bands grid.
- `layout.tsx` fetches bands and builds a `bandDisplayNames` map, passed to `SiteHeader` → `GlobalSearch` so search results show band names from the DB.

### Docs
- `docs/contributor/model_development.md`: New guide covering the 4-step model addition workflow with code templates.
- `docs/reference/specifications/data_strategy.md`: Added "Band Registry" section; removed "shared band discovery" and "ID normalization" from gaps.
- `docs/contributor/developer_guide/architecture.md`: Added "Band Registry" and "Model Platform" sections; updated non-negotiable rules.

## Validation
- `npm run lint` (web): clean
- `npm run build` (web): clean — all routes compile
- `npx tsc --noEmit` (web): clean
- `uv run ruff check` on Python files touched: all pass

## Follow-Up
## Next Step

Apply the `bands` migration to Supabase (done — verified 6 rows). Follow-up: clean up unused `BAND_CONFIG` / `ACTIVE_BANDS` from `apps/web/src/lib/config.ts` now that the dynamic pages source bands from Supabase.
