# 2026-03-21 Session Log 06

## Goal
Finish the website dynamic-band migration so the `bands` Supabase registry is the runtime source of truth for band metadata and invalid `?band=` values no longer silently fall back to Goose.

## Constraints
- Keep `MODEL_CONFIG` static in code.
- Do not reintroduce hardcoded website band metadata.
- Preserve missing-env behavior for routes when Supabase is unavailable.
- Leave the website routes build-clean before handing off.

## Commands Run
- `git checkout -b feat/web-dynamic-band-cleanup`
- `npm run lint:web`
- `npm run build:web`
- `npm run test:web:smoke:list`
- `npm run test:web:smoke`
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npm run test:web:smoke`
- `git add ...`
- `git commit -m "feat(web): finish dynamic band branch verification"`
- `git push -u origin feat/web-dynamic-band-cleanup`
- `gh api repos/connorkitchings/JamBandNerd/commits/fd4b2ff/status`
- Protected preview verification via bypass cookie against `jambandnerd-git-feat-web-dynami-14cf69-connorkitchings-projects.vercel.app`

## Files Changed
- `apps/web/src/lib/config.ts`
- `apps/web/src/lib/data.ts`
- `apps/web/src/app/page.tsx`
- `apps/web/src/app/explorer/page.tsx`
- `apps/web/src/app/compare/page.tsx`
- `apps/web/src/app/performance/page.tsx`
- `apps/web/src/app/last-show/page.tsx`
- `apps/web/src/components/filter-links.tsx`
- `apps/web/src/components/dashboard-side-nav.tsx`

## What Changed
- Removed static website band metadata (`BAND_CONFIG`, `BAND_ID_COLUMNS`, `ACTIVE_BANDS`) from `config.ts`.
- Changed `BandSlug` to a runtime string slug and kept only `DEFAULT_BAND_SLUG` plus model config in `config.ts`.
- Added `resolveBandSelection()` and `getBandContext()` in the server data layer so band lookup now goes through the `bands` table.
- Updated accuracy, show-detail, setlist, last-show, and global-search paths to use `shows_table` and `id_column` from Supabase instead of hardcoded config.
- Updated band-aware routes to validate the requested slug before querying route data so invalid slugs now render the intended "Band not found" state.
- Removed stale component casts that assumed band slugs were a closed compile-time union.

## Validation
- `npm run lint:web`: passed
- `npm run build:web`: passed
- `npm run test:web:smoke:list`: passed
- `npm run test:web:smoke`: failed in the sandbox before test execution because Playwright Chromium aborted on launch with `SIGABRT`
- `PLAYWRIGHT_BROWSERS_PATH=/Users/connorkitchings/.cache/ms-playwright npm run test:web:smoke`: passed outside the sandbox
- Vercel preview deployment for commit `fd4b2ff`: passed
- Protected hosted route verification passed for `/`, `/explorer`, `/compare`, `/performance`, `/last-show`, `/about`, `/preview/tables`
- `/predictions` returned the expected `307` redirect to `/`
- Invalid `?band=definitely-not-a-band` on `/` rendered the explicit "Band not found" state on the preview
- Non-default band route spot checks passed:
  `/?band=phish&model=notebook`
  `/explorer?band=billy&model=notebook`
  `/performance?band=um&model=ckplus`

## Next Step
Open a PR from `feat/web-dynamic-band-cleanup`, let `Website Quality` finish, and merge once the GitHub/Vercel checks are green.
