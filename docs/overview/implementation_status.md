# JamBandNerd Implementation Status

**Last Updated**: 2026-04-13
**Project Version**: 0.2.1

## Overall Status

JamBandNerd has a production-ready website-first product surface and a production-capable data platform with explicit degraded-mode handling for volatile upstreams.

- **Pipeline status**: stable and production-capable, with WSP degraded-mode handling in CI
- **Prediction status**: stable across supported models and bands, with strict workflow failures for supported-model no-output cases and bounded degraded-data reuse
- **Automation status**: daily GitHub Actions workflows in place, including per-band health reporting
- **Frontend status**: `apps/web` is the sole product surface

## Implemented Platform Components

### Data and Modeling

- Band-specific collectors for 6 bands: Goose, Phish, Eggy, Billy Strings, Widespread Panic, Umphrey's McGee
- Supabase raw tables plus unified prediction and accuracy storage
- In-memory transforms with `reference_date` protection
- Notebook and Deal promoted prediction models
- CK+ retained as a retired historical baseline with stored historical outputs
- Backtesting and rolling accuracy aggregation
- Unified `show_id` convention across all bands (Phish migration complete)

### Prediction Storage

- Canonical JSON prediction tables (`predictions_notebook`, `predictions_ckplus`, `predictions_deal`)
- Derived per-song projection (`prediction_songs`) for website reads
- Automatic stale-row cleanup in `replace_prediction_projection()`
- Rebuildable projection via `scripts/rebuild_prediction_songs.py`

### Operations

- `scripts/run_optimized_pipeline.py` as the canonical end-to-end entrypoint
- 9 GitHub Actions workflows:
  - **Daily Data Pipeline**: Scheduled collection, predictions, backtests, validation
  - **Fantasy Goose**: Auto-play Fantasy Goose after daily pipeline success
  - **Backfill Predictions**: Manual historical prediction regeneration
  - **Live Show Tracker**: Manual live setlist polling for goose, phish, wsp
  - **Repo Quality**: CI lint + targeted pytest on PRs and pushes to main
  - **Website Quality**: CI lint + build + smoke tests on PRs and pushes to main
  - **Hosted Website Smoke**: Daily smoke test against live deployed website
  - **Dependency Audit**: Weekly pip-audit of locked dependencies
  - **Test Secrets**: Manual secret availability verification
- Validation and data-quality checks in the pipeline workflow
- Security/dependency maintenance workflows
- Dependency audit locked to remediated package versions

### Website

- 10 public routes: `/`, `/predictions`, `/performance`, `/compare`, `/replay`, `/explorer` (redirect), `/last-show`, `/about`, `/contact`, `/data-use`
- Admin setlist submission at `/admin/setlist`
- Dynamic band and model discovery from Supabase
- Vercel deployment with native GitHub integration
- Mobile-responsive design

### WSP Data Collection

- Playwright-based browser automation for reliable scraping
- Versioned parser profiles with DOM fingerprinting
- TourWrangler fallback for missing Everyday Companion setlists
- HTML fixture regression tests

## Active Priorities

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
- WSP Notebook remains supported alongside Deal. Daily workflow commands now require fresh output for both models so silent no-op runs fail fast instead of leaving stale rows behind.
- Degraded-mode reuse is no longer unbounded: supported predictions and accuracy are audited against a `48h` freshness window, and stale supported predictions now escalate the band job even when collection degraded gracefully.
- Manual `skip_accuracy=true` dispatches still record stale supported accuracy, but they do not fail solely because accuracy regeneration was explicitly skipped.
- Pipeline and schema stability remain the priority during ongoing website operations.
- Phish now uses `show_id` consistently with all other bands (migration applied 2026-04-06).
