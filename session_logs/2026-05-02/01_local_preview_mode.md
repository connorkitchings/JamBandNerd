## Session 2026-05-02 — Local Preview Mode For Website Review

## Summary
Added a seeded local preview mode to the website data layer so the full JamBandNerd site renders without live Supabase env vars during local review. Updated docs and playbook guidance to describe the fallback explicitly.

## Goal
Make the website fully viewable locally for design review, including homepage teasers and the key data-heavy routes, without relying on Supabase.

## Changes
- Added `apps/web/src/lib/data/preview.ts` with seeded band, prediction, accuracy, replay, and setlist fixtures.
- Switched the website data fetchers to preview mode when not running on Vercel and Supabase env vars are absent.
- Updated `README.md`, `apps/web/README.md`, and `docs/operations/website_delivery.md` to describe the local preview behavior.
- Added `apps/web/tests/unit/local-preview.test.ts` for the preview-mode contract.
- Added a playbook note for future local-review sessions.

## Validation
- `npm run build:web`
- `npm run verify:web`
- Confirmed local routes render preview content at `http://127.0.0.1:3001/`, `/predictions?band=goose&model=deal`, `/last-show?band=goose`, and `/replay?band=goose`

## Notes
- Preview mode is enabled automatically when `VERCEL !== "1"` unless `JAMBNERD_PREVIEW_MODE=0` is set.
- The local site server is still running on `127.0.0.1:3001` for manual review.
