# Session Log: v1.0 Pre-Launch Comprehensive Site Review

Date: 2026-05-17

## Goal

Perform a comprehensive review of every page, component, and shared lib in `apps/web/` against the Vercel Web Interface Guidelines. Produce a punch list for targeted fixes before the v1.0 deployment to production. No implementation — planning only.

## Constraints

- Read-only review. No code changes made to web app files.
- Apply Web Interface Guidelines from vercel-labs/web-interface-guidelines.
- Cover accessibility, UX, content, code quality, and polish.
- The 50-capped backfill from the prior session (`session_logs/2026-05-17/04_50_capped_backfill.md`) was already completed and committed.

## Summary

Reviewed 10 pages, 25 components, 5+ shared lib files, and `globals.css`. Applied the full Vercel Web Interface Guidelines checklist. Found 30 actionable items across 5 priority tiers.

Output artifact: `docs/operations/v1_punch_list.md` — the canonical pre-launch punch list.

### Findings breakdown

| Priority | Count | Key themes |
|----------|-------|------------|
| Critical (a11y) | 6 | Missing `focus-visible:ring` on 7 components, `aria-expanded`/`aria-controls` gaps, `<label>` linkage issue, no "no results" state in song search, homepage mobile CTAs hidden, heading hierarchy undocumented |
| UX / Functional | 9 | Song name truncation missing on mobile, `normalizeSongName`/Top-K computation duplicated across pages, last-show only shows Top-10 not Top-25/50, copy mismatch on predictions page, double `editorial-panel` nesting, prediction-hero headline priority inverted, chart scaling on wide screens |
| Content / Copy | 4 | ASCII dots vs ellipsis, straight vs curly quotes, misplaced license grant on contact page, "slippage" jargon on performance page |
| Code Quality | 5 | Repeated 4-state error/empty boilerplate across all pages, env var serialization to client, Supabase client re-creation in LiveTracker, hardcoded teaser bands vs Supabase source of truth, 6x array iteration in performance page |
| Minor / Polish | 6 | Missing `autocomplete`/`spellCheck` on search input, FAQ all-closed by default, dead CSS gradients, overloaded PredictionHero component, band pill grid duplication |

## Files Reviewed

Every file in:
- `apps/web/src/app/` — 10 pages + layout + CSS
- `apps/web/src/components/` — 25 components
- `apps/web/src/lib/` — data, format, navigation, show-status, config, site

## Validation

- No code changes to web app — no web verification needed.
- `npm run verify:clean` passed (no dirty files).
- The 50-capped backfill was validated in the prior session (16/16 tests, all 5 bands exact 50-row retention).

## Next Step

Work through `docs/operations/v1_punch_list.md` item by item over several sessions before merging `dev` to `main` for v1.0 production launch. Start with the 6 critical a11y items.

## Independent Follow-Up

After the initial read-only review, a separate route-level pass was completed before re-reading this log or the punch list. It covered the public routes, `/admin/setlist`, `/preview/tables`, and removed routes `/compare` and `/explorer` at desktop and mobile sizes.

Implemented immediately:
- Added a stable `Admin Access` `<h1>` plus status text to the `/admin/setlist` session-checking state.
- Changed `/replay` so the prediction board and actual setlist stack full-width, preserving song names in the desktop prediction table and removing the stretched empty setlist panel.

Added to `docs/operations/v1_punch_list.md`:
- Follow-up finding for duplicate-looking `/performance` recent ledger rows, pending data contract review before any UI/data-layer change.

Validation:
- `npm run test:web:smoke:list`
- Local Playwright route audit with screenshots under `/tmp/jbn-site-review-shots`
- `npm run lint:web`
- `npm run build:web`
- `npm run verify:web`
- `npm run verify:docs`
