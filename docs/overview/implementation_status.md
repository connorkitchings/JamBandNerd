# JamBandNerd Implementation Status

**Last Updated**: 2026-04-07
**Project Version**: 0.1.0

## Overall Status

JamBandNerd has a production-ready website-first product surface and a production-capable data platform with explicit degraded-mode handling for volatile upstreams.

- **Pipeline status**: stable and production-capable, with WSP degraded-mode handling in CI
- **Prediction status**: stable across supported models and bands
- **Automation status**: daily GitHub Actions workflows in place, including per-band health reporting
- **Frontend status**: `apps/web` is the sole product surface

## Implemented Platform Components

### Data and Modeling

- Band-specific collectors for 6 bands: Goose, Phish, Eggy, Billy Strings, Widespread Panic, Umphrey's McGee
- Supabase raw tables plus unified prediction and accuracy storage
- In-memory transforms with `reference_date` protection
- Notebook and CK+ production prediction models
- Deal (XGBoost-based) model registered and wired, gated off from pipeline and web while experimental
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

- Promote Deal model to production after evaluation
- Public API for external consumers
- Real-time/live-show workflows
- User accounts or personalization

## Notes

- The Streamlit app has been retired. The website at `apps/web` is the sole product surface.
- WSP remains part of the supported catalog, but CI now handles Everyday Companion blocking as an explicit degraded state instead of treating it as a full cross-band outage.
- Pipeline and schema stability remain the priority during ongoing website operations.
- Phish now uses `show_id` consistently with all other bands (migration applied 2026-04-06).
