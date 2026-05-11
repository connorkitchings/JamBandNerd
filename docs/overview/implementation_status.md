# JamBandNerd Implementation Status

**Last Updated**: 2026-05-11
**Project Version**: 0.3.0

## Overall Status

JamBandNerd has a production-ready website-first product surface and a production-capable data platform with explicit degraded-mode handling for volatile upstreams.

- **Pipeline status**: stable and production-capable, with WSP degraded-mode handling in CI
- **Prediction status**: single-model-per-band platform cutover in progress, with strict workflow failures for no-output cases and bounded degraded-data reuse
- **Automation status**: daily GitHub Actions workflows in place, including per-band health reporting
- **Frontend status**: `apps/web` is the sole product surface

## Implemented Platform Components

### Data and Modeling

- Band-specific collectors for 6 bands: Goose, Phish, Eggy, Billy Strings, Widespread Panic, Umphrey's McGee
- Supabase raw tables plus single-model `setlist_*` prediction and accuracy storage
- In-memory transforms with `reference_date` protection
- One registered active model version per Phase A band
- Legacy Notebook/Deal/CK+ retained for baseline comparison and rollback context
- Backtesting with retained completed-show lineage through `setlist_results`
- Unified `show_id` convention across all bands (Phish migration complete)

### Prediction Storage

- Canonical live prediction rows in `setlist_predictions`
- Derived per-song projection in `setlist_prediction_songs` for website reads
- Retained completed-show boards in `setlist_results`
- Per-show metrics in `setlist_accuracy`

### Operations

- `scripts/run_optimized_pipeline.py` as the canonical end-to-end entrypoint
- 9 GitHub Actions workflows:
  - **Daily Data Pipeline**: Scheduled collection, predictions, backtests, validation
  - **Fantasy Goose**: Auto-play Fantasy Goose after daily pipeline success
  - **Backfill Predictions**: Manual historical prediction regeneration
  - **Live Show Tracker**: Manual live setlist polling for goose, phish, wsp
  - **Repo Quality**: CI Python verification + docs build + clean-worktree guard on PRs and pushes to main
  - **Website Quality**: CI smoke inventory + lint + build + smoke + clean-worktree guard on PRs and pushes to main
  - **Hosted Website Smoke**: Daily smoke test against live deployed website
  - **Dependency Audit**: Weekly pip-audit of locked dependencies
  - **Test Secrets**: Manual secret availability verification
- Validation and data-quality checks in the pipeline workflow
- Security/dependency maintenance workflows
- Dependency audit locked to remediated package versions

### Website

- 7 public routes: `/`, `/predictions`, `/performance`, `/last-show`, `/about`, `/contact`, `/data-use`
- Admin setlist submission at `/admin/setlist`
- Dynamic band discovery from Supabase
- Vercel deployment with native GitHub integration
- Mobile-responsive design

### WSP Data Collection

- Playwright-based browser automation for reliable scraping
- Versioned parser profiles with DOM fingerprinting
- TourWrangler fallback for missing Everyday Companion setlists
- HTML fixture regression tests

## Active Priorities

### Current Upstream Blockers

- WSP full-audit readiness is blocked by recent Everyday Companion pages that
  expose show pages but no setlist table for May 8 and May 9, 2026. Treat this
  as an upstream data-availability blocker, not a model-promotion blocker.
- Billy full-audit readiness is blocked by `bmfsdb.com` returning HTTP 500
  during source reachability preflight.
- Until both upstreams can publish current website-facing rows again, defer the
  full five-band Supabase audit and preserve the already-validated Goose,
  Phish, and UM readiness fixes.

### Website Operations

- Keep `apps/web` production-ready through Vercel deployment checks and GitHub Actions verification
- Maintain pipeline monitoring, prediction freshness validation, and hosted verification paths
- Continue refining current routes and explanatory content where it improves the live website experience

### Optional Future Expansion

- Public API for external consumers
- Real-time/live-show workflows
- User accounts or personalization

## Notes

- The website at `apps/web` is the sole maintained product surface.
- WSP remains part of the supported catalog, but CI now handles Everyday Companion blocking as an explicit degraded state instead of treating it as a full cross-band outage.
- Daily workflow commands now require fresh output for each active band's registered model version so silent no-op runs fail fast instead of leaving stale rows behind.
- Degraded-mode reuse is no longer unbounded: supported predictions and accuracy are audited against a `48h` freshness window, and stale supported predictions now escalate the band job even when collection degraded gracefully.
- Manual `skip_accuracy=true` dispatches still record stale supported accuracy, but they do not fail solely because accuracy regeneration was explicitly skipped.
- Pipeline and schema stability remain the priority during ongoing website operations.
- Phish now uses `show_id` consistently with all other bands (migration applied 2026-04-06).
