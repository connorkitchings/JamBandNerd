# GitHub Actions

This repository uses 9 GitHub Actions workflows for pipeline automation, CI quality gates, and operational monitoring.

## Workflow Summary

| Workflow | File | Schedule | Manual | PR/Push | Bands |
|----------|------|----------|--------|---------|-------|
| Daily Data Pipeline | `daily-pipeline.yml` | 19:00 UTC daily | Yes | -- | All 6 |
| Fantasy Goose | `fantasy-goose.yml` | After daily pipeline | Yes | -- | goose |
| Backfill Predictions | `backfill-predictions.yml` | -- | Yes | -- | All 6 |
| Live Show Tracker | `live-tracker.yml` | -- | Yes | -- | goose, phish, wsp |
| Repo Quality | `repo-quality.yml` | -- | -- | PR + push main | -- |
| Website Quality | `web-quality.yml` | -- | -- | PR + push main | -- |
| Hosted Website Smoke | `hosted-web-smoke.yml` | 20:30 UTC daily | Yes | -- | -- |
| Dependency Audit | `dependency-audit.yml` | Mon 14:00 UTC | Yes | -- | -- |
| Test Secrets | `test_secrets.yml` | -- | Yes | -- | -- |

---

## Daily Data Pipeline

The primary production workflow. Collects raw data, generates predictions, runs backtests, and validates freshness for all supported bands.

- **Triggers**:
  - `schedule`: `0 19 * * *` (daily at 19:00 UTC / 3:00 PM ET during DST)
  - `workflow_dispatch` with inputs: `band` (`all` or a single band), `skip_accuracy` (boolean)

- **Steps per band** (parallel matrix):
  1. Compute collection preflight via `scripts/collection_preflight.py`
  2. Run data collection via `scripts/run_{band}_collection.py` (with retry logic)
  3. Verify data freshness via `scripts/verify_data_freshness.py`
  4. Generate predictions for Notebook and CK+ models via `scripts/generate_predictions.py`
  5. Validate prediction tables via `scripts/validate_prediction_tables.py`
  6. Run backtests and save aggregate accuracy (skippable via `skip_accuracy`)
  7. Validate accuracy tables via `scripts/validate_accuracy_tables.py`
  8. Write per-band status summary

- **Band matrix**: Dynamically built from `scripts/get_all_bands.py`. Current bands: goose, phish, eggy, billy, um, wsp.
- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; `PHISH_API_KEY` for Phish only.

### WSP Degraded-Mode Handling

- WSP installs Playwright (Firefox) for scraping reliability.
- Upstream blocking without recent completed-show gaps is treated as **degraded**.
- Degraded runs skip prediction/backtest regeneration and report whether the website is reusing prior data.
- WSP upstream blocking that leaves recent completed-show data unusable is a hard failure.

### Failure Policy

- Non-WSP collection failures are hard failures.
- WSP collector regressions are hard failures.
- WSP upstream blocking is degraded only when recent completed-show data is still usable.
- Recent completed-show setlist gaps from upstream blocking remain hard failures.
- The workflow summary shows per-band health, execution mode, missing-setlist counts, and prediction handling.

### Optional Notifications

If `DISCORD_WEBHOOK_URL` is set in GitHub Secrets, the workflow posts a success/failure message.

---

## Fantasy Goose

Automatically plays Fantasy Goose using JamBandNerd notebook predictions for Goose.

- **Triggers**:
  - `workflow_run`: After a successful `Daily Data Pipeline` run on `main`
  - `workflow_dispatch` with inputs: `date` (YYYY-MM-DD), `dry_run` (boolean)

- **Behavior**:
  - Logs in to Fantasy Goose using stored credentials
  - Reads the authenticated show dropdown and song catalog
  - Selects the Goose show for the target date when the pick cutoff is open
  - Fetches Goose `notebook` predictions for the exact `reference_date`
  - Maps the top 8 songs onto Fantasy Goose song ids and submits

- **Failure policy**:
  - `mapping_failed` or `missing_predictions` fails the workflow
  - `no_show_tonight`, `cutoff_passed`, `already_submitted`, and `dry_run` are non-error no-ops

- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `FG_USER_EMAIL`, `FG_PASSWORD`

---

## Backfill Predictions

Regenerates historical predictions for one or more band/model combinations.

- **Triggers**: `workflow_dispatch` only
- **Inputs**: `band` (all or specific), `model` (all, notebook, ckplus), `dry_run` (boolean)
- **Flow**:
  1. Setup job builds a band/model matrix
  2. Per-combination backfill job fetches prediction dates via `scripts/get_prediction_dates.py`, regenerates each via `scripts/generate_predictions.py`, validates via `scripts/validate_prediction_tables.py`
  3. Summary job writes results
- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

---

## Live Show Tracker

Tracks live shows by polling for setlist updates during a performance.

- **Triggers**: `workflow_dispatch` only
- **Inputs**: `band` (goose, phish, wsp), `date` (YYYY-MM-DD), `interval` (default 60s), `max_iterations` (default 300), `bsky_handle` (WSP only)
- **Behavior**: Runs `scripts/run_live_tracker.py` with Playwright for WSP. Polls for setlist updates and publishes them.
- **Concurrency**: One tracker per band+date combo; cancels in-progress runs.
- **Timeout**: 360 minutes (6 hours)
- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; `PHISH_API_KEY` for Phish only

---

## Repo Quality

CI quality gate for the Python pipeline codebase.

- **Triggers**: `pull_request` and `push` to `main`
- **Steps**:
  1. Set up Python 3.12 + uv
  2. `ruff check src tests scripts`
  3. Targeted pytest on `tests/models`, `tests/pipeline/test_run_backtest.py`, `tests/pipeline/test_run_optimized_pipeline.py`

---

## Website Quality

CI quality gate for the `apps/web` Next.js website.

- **Triggers**: `pull_request` and `push` to `main`
- **Steps**:
  1. Set up Node 22 + `npm ci`
  2. Install Playwright Chromium
  3. `npm run lint:web`
  4. `npm run build:web`
  5. `npm run test:web:smoke`

---

## Hosted Website Smoke

Daily smoke test against the live deployed website.

- **Triggers**:
  - `schedule`: `30 20 * * *` (daily at 20:30 UTC)
  - `workflow_dispatch` with input: `base_url` (default `https://jambandnerd.com`)
- **Steps**: Runs `npm run test:web:smoke:hosted` with Playwright Chromium
- **Secrets**: `VERCEL_PROTECTION_BYPASS_TOKEN` (for preview URLs)

---

## Dependency Audit

Weekly security audit of locked Python dependencies.

- **Triggers**:
  - `schedule`: `0 14 * * 1` (Mondays at 14:00 UTC)
  - `workflow_dispatch`
- **Steps**: Exports locked requirements via `uv export`, then runs `pip-audit` against them
- **Timeout**: 20 minutes

---

## Test Secrets

Debugging utility to verify GitHub Secrets are configured correctly.

- **Triggers**: `workflow_dispatch` only
- **Behavior**: Checks that `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set. Warns if `PHISH_API_KEY` is missing.

---

## Data Validation

All collection scripts use **warning-only validation**:

- **Type mismatches** are logged as warnings but don't block data inserts after coercion
- **Missing required columns** and **nullable violations** fail the write
- Validation warnings appear in GitHub Actions logs for monitoring
- No `--skip-validation` flags needed in the workflow

For more details, see:
- `VALIDATION_IMPROVEMENTS.md` - Complete documentation
- `TEST_REPORT_VALIDATION.md` - Testing and verification results

## Manual Recovery

For manual recovery or migration workflows:

- `scripts/audit_raw_data.py` — inspect raw data before targeted re-ingestion
- `scripts/rebuild_derived_data.py` — rebuild predictions and accuracy after schema changes
- `scripts/rebuild_prediction_songs.py` — rebuild the `prediction_songs` projection from canonical tables
- `scripts/wipe_band_data.py` — clear derived outputs per band/model
