## Session 2026-05-01 — Comprehensive Fixes

## Summary
Applied 45 fixes across four tiers: critical (5), high/medium (28), low-severity (10), and operational resilience (3 after CI failure investigation). 393 tests pass, 66% coverage, web build verified, verify:all green.

## Goal
Comprehensive repo review → implement fixes across organization, architecture, performance, data workflows, backend, and frontend. Followed by investigating and hardening against real CI failures (WSP + Phish upstream outages on May 1).

## Validation Status
- ruff check: All checks passed
- black --check: All files formatted
- pytest: 393 passed, 6 skipped, 66% coverage
- next build: Compiled successfully (10/10 static pages)
- Playwright smoke: 11 passed, 11 skipped
- pre-commit: Installed
- mypy: 295 pre-existing errors, 0 new from this session (types-requests installed)

## Commands Run
- `npm run verify:python` (multiple times throughout)
- `npm run verify:web` (Turbopack root fix + loading.tsx prop fixes)
- `npm run verify:all` (final gate — Python, docs, web all green)
- `npm run verify:types` (baseline: 295 pre-existing, 14 import-untyped fixed with types-requests)
- `gh run view` (CI failure investigation for WSP/Phish)
- `npm ci` (install web dependencies for build)
- `uv pip install pre-commit types-requests`
- `uv run pre-commit install`
- `uv run black src tests scripts`
- `uv run ruff check --fix src tests scripts`

## Critical Fixes (prior session)

| Fix | Files | Change |
|-----|-------|--------|
| WSP sys.exit(1) kills orchestrator | `scripts/run_wsp_collection.py` | Replaced sys.exit with raise RuntimeError |
| run_live_tracker.py broken imports | `scripts/run_live_tracker.py` | Fixed imports to use actual normalizer modules |
| _parse_date() duplicated 3x | `utils.py`, `goose/eggy/wsp/normalizer.py` | Extracted to shared utils, references DATE_FORMATS |
| WSP collector imports Supabase | `wsp/collector.py` | Removed Supabase dependency, moved check to orchestrator |
| setlist_reviewer.py in shared dir | `wsp/reviewer.py` (moved) | Moved WSP-only code into wsp/ |

## Phase 1 — Quick Wins (11 items)
- Added npm Dependabot ecosystem
- Fixed empty billy/__init__.py and predictions/__init__.py
- Added cache: "npm" to repo-quality.yml
- Added CI artifacts to .gitignore
- Created root .env.example
- Fixed test_data_collection.py copy-paste bug (duplicate assert block)
- Removed unused sample_data_dir fixture from conftest.py
- Disabled supabase seed.sql (referenced but missing)
- Fixed .env.local.example service-role key contradiction (added warning comment)
- Deleted unused dashboard-analysis.tsx component

## Phase 2 — Frontend (6 items)
- Created middleware-like proxy (Next.js 16 uses proxy.ts natively, not middleware.ts)
- Added loading.tsx to 5 data-heavy routes (predictions, performance, compare, replay, last-show)
- Added root error.tsx error boundary
- Deduplicated 7 frontend utility functions:
  - average() → lib/math.ts
  - buildReplayHref() → lib/format.ts
  - normalizeSongName() → shared from lib/song-board.ts
  - Venue helpers → removed private copies from next-show.ts, import from parsers.ts
- Replaced hardcoded HOME_TEASER_BANDS with dynamic teaserBands from getBands()
- Made admin band list dynamic via embedded JSON from layout
- Split song-board.tsx into server (song-board.tsx) + client (tier-section.tsx)

## Phase 3 — Data/Pipeline (7 items)
- Fixed ABC collect_setlists() signature (List[Dict] not Optional[List[str]])
- Extracted shared _is_target_artist() to base BandCollector class
- Extracted shared upsert_table() to scripts/common.py (Goose + Eggy use it)
- Added rate limiting + success/failure tracking to Billy collector's direct session.get() calls
- Documented WSP custom session bypass (Cloudflare-aware, intentional)
- Changed Phish upsert from re-raise to return (consistent with Goose/Eggy)
- Added retry with backoff to ensure_source_reachable() in common.py

## Phase 4 — Documentation (1 item)
- github_actions.md already current — no changes needed

## Phase 5 — Quality Infrastructure (4 items)
- Created .pre-commit-config.yaml (ruff + standard hooks)
- Added --cov=src --cov-fail-under=50 to verify:python
- Added verify:types script (mypy baseline: 14 pre-existing import-untyped errors)
- Created tests/support/stubs.py with shared SupabaseQueryStub/SupabaseClientStub

## Phase 6 — Configurable Baseline (1 item)
- Replaced PRIMARY_BASELINE_SLUG="ckplus" with get_promotion_baseline()
- Default baseline is now "deal" (strongest promoted model)
- Dynamic check key names (e.g., avg_recall_k10_beats_deal)
- Updated compare_models.py DEFAULT_BASELINES to ("deal", "notebook")

## Low-Severity Fixes (10 items)
- Deleted dead models/serialization.py (zero imports)
- Replaced admin/layout.tsx inline styles with Tailwind
- Created custom not-found.tsx 404 page
- Updated pipeline_optimization.md 3-band → 6-band matrix
- Removed band-specific if band=="wsp" from setlist_parser.py
- Fixed timezone-aware datetime comparison in deal/model.py
- Reverted next/dynamic for live-tracker (incompatible with server component module level)
- Consolidated setup-uv+setup-python in 3 workflows (live-tracker, fantasy-goose, backfill)
- Skipped: artifact upload merge (complex cross-workflow coupling)
- Skipped: CK+ removal policy (intentionally retained), Billy normalizer pattern (valid divergence), standalone docs workflow (unnecessary)

## Operational Resilience Fixes (3 items — after CI failure investigation)

### CI Investigation
May 1 daily pipeline failed for WSP and Phish. Both had shows the night before.

- **Phish**: phish.net returned continuous 502 errors for 33+ minutes. All 3 shell-level retry attempts exhausted the urllib3 retry pool immediately, then waited 30s between attempts — total coverage ~90 seconds against a 33-minute outage.

- **WSP**: everydaycompanion.com had a DOM change on the 2026-04-30 show page ("No set markers found on setlist page"). The fallback chain (PanicStream → TourWrangler) ran but returned empty with zero diagnostic output. The PanicStream show page exists at the correct URL (`widespread-panic-04-30-2026-new-orleans-la`) but the fallback code silently swallows all failure causes.

### Fixes Applied

1. **PanicStream diagnostic logging** (`wsp/panicstream.py` + `wsp/orchestration.py`)
   - All silent `return []` paths now log warnings: index page fetch failed, no match on year index, show page fetch failed, HTML not parseable
   - Fallback loop logs when any source returns empty rows

2. **Phish outer retry** (`data_collection/base.py` `_fetch_from_endpoint()`)
   - Added 60s/120s exponential backoff for 502/503/504 errors after urllib3 retries exhaust
   - Combined with 3 shell-level retries: ~21 minutes of outage coverage

3. **WSP degraded classification** (`wsp/status.py`)
   - When `ec_request_failed` ≤ 1 AND data was still collected (shows/songs > 0): classifies as `degraded_upstream_stale` instead of `failed_upstream_stale`
   - Pipeline continues with prior predictions instead of hard-failing on a single very-recent missing setlist

## Web Build Fix
- Added turbopack.root to next.config.ts (points to monorepo workspace root)
- Fixed PageHero prop (subtitle → description) and SectionCard prop (missing title) in all 5 loading.tsx

## Verification
- ruff check: All checks passed
- black --check: All files formatted
- pytest: 393 passed, 6 skipped, 66% coverage
- next build: Compiled successfully (10/10 static pages)
- pre-commit: Installed

## Files Changed
~75 files across src/, scripts/, tests/, apps/web/, docs/, .github/, config files. 70 modified + new files in working tree on branch `dev`.

## Next Step
Commit to `dev`, push, and open PR against `main`. Manual trigger WSP + Phish collection tomorrow via `workflow_dispatch` to verify the operational fixes. Monitor CI logs for the new PanicStream diagnostic output to identify root cause of 4/30 fallback failure.

## Post-Commit Dev Fixes

- **Teaser band ordering**: Fixed to Phish, WSP, Billy, Goose (not alphabetical). Added shorthand labels (WSP for Widespread Panic, Billy for Billy Strings) via `TEASER_LABELS` mapping.
- **Supabase dev-mode anon key bypass**: `server.ts` `hasSupabaseEnv()` and `getSupabaseServerClient()` now skip `looksLikeSecretKey()` check in development mode. Required because this Supabase project only exposes keys prefixed with `sb_secret_`.
- **Deal mobile layout**: Experimented with stacked vertical layout, reverted to original single-line format per user preference.
