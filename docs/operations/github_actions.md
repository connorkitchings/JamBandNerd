# GitHub Actions

This repository uses 9 GitHub Actions workflows for pipeline automation, CI quality gates, and operational monitoring.

## Workflow Summary

| Workflow | File | Schedule | Manual | PR/Push | Bands |
|----------|------|----------|--------|---------|-------|
| Daily Data Pipeline | `daily-pipeline.yml` | 19:00 UTC daily | Yes | -- | All 6 |
| Fantasy Goose | `fantasy-goose.yml` | After daily pipeline | Yes | -- | goose |
| Sync Retained Corpus | `backfill-predictions.yml` | -- | Yes | -- | All 6 |
| Live Show Tracker | `live-tracker.yml` | -- | Yes | -- | goose, phish, wsp |
| Repo Quality | `repo-quality.yml` | -- | -- | PR + push main | -- |
| Website Quality | `web-quality.yml` | -- | -- | PR + push main | -- |
| Hosted Website Smoke | `hosted-web-smoke.yml` | 22:00 UTC daily | Yes | -- | -- |
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
  4. Generate live next-show predictions for Notebook and Deal via `scripts/generate_live_predictions.py`
  5. Validate live prediction tables via `scripts/validate_prediction_tables.py`
  6. Sync the retained completed-show corpus via `scripts/sync_retained_prediction_corpus.py --window 50` (skippable via `skip_accuracy`; both models use the same last-50 window; emits `backtest_incremental_all_scored` output through the underlying scorer)
  8. Validate accuracy tables via `scripts/validate_accuracy_tables.py` (passes `--skip-freshness` when all shows already scored)
  9. Audit supported-model freshness via `scripts/check_supported_model_freshness.py`
  10. Audit website Supabase tables via `scripts/audit_supabase_tables.py` (passes `--skip-accuracy` when all shows already scored)
  11. Write per-band status summary and enforce stale-freshness escalation after artifacts are uploaded

- **Band matrix**: Dynamically built from `scripts/get_all_bands.py`, which returns the repo-authoritative automation band list. Current bands: goose, phish, eggy, billy, um, wsp.
- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; `PHISH_API_KEY` for Phish only.

### WSP Degraded-Mode Handling

- WSP installs Playwright (Firefox) for scraping reliability.
- Upstream blocking without recent completed-show gaps is treated as **degraded**.
- Degraded runs skip prediction/backtest regeneration and report whether the website is reusing prior data.
- WSP upstream blocking that leaves recent completed-show data unusable is a hard failure.
- WSP Notebook remains an actively supported model surface. It is not deprecated for WSP.
- The daily workflow now runs Notebook and Deal with strict output requirements. A supported model that exits without writing fresh predictions or per-show backtest rows is treated as a workflow failure instead of a silent success.
- Supported-model reuse during degraded mode is now bounded:
  - if reused prediction freshness stays within `48h`, the band can remain degraded but non-failing
  - if supported-model prediction freshness exceeds `48h`, the band job fails after the status artifact and summary are written
  - accuracy uses the same `48h` window, except manual `skip_accuracy=true` runs report stale accuracy informationally and do not fail solely for skipped accuracy regeneration
- The sampled 2026-04-13 WSP Notebook freshness gap should therefore be treated as a real operational defect that requires regeneration or workflow investigation, not as acceptable drift.

### Eggy Cloudflare Bypass

- Eggy (`thecarton.net`) is behind Cloudflare bot protection with JS challenges.
- The Eggy collector tries standard HTTP requests first; on 403 it falls back to Playwright (Firefox) via the shared `data_collection/browser.py` module.
- Playwright is installed in CI for both WSP and Eggy bands.
- Because browser-backed collection and automation import Playwright directly at runtime, it is a locked runtime dependency rather than a dev-only tool.
- If Cloudflare is lifted, Eggy automatically skips Playwright and uses direct HTTP.

### Failure Policy

- Non-WSP collection failures are hard failures.
- WSP collector regressions are hard failures.
- WSP upstream blocking is degraded only when recent completed-show data is still usable.
- Recent completed-show setlist gaps from upstream blocking remain hard failures.
- Supported-model freshness is a separate enforcement path from collection success:
  - when `WORKFLOW_STATE == "degraded"`: stale predictions and stale accuracy emit `::warning::` only (no job failure). Degraded bands cannot regenerate predictions; staleness is expected and surfaced in the summary
  - when `WORKFLOW_STATE != "degraded"`: stale predictions and stale accuracy are hard failures (unless `skip_accuracy=true` or `backtest_incremental_all_scored=true`). If regeneration completed but freshness is still stale, something else is wrong
  - when incremental backtest finds all shows in the window already scored, accuracy staleness is expected and not enforced (scores are immutable; the backtest emits `backtest_incremental_all_scored=true`)
  - the `backtest_incremental_all_scored` signal gates three steps: `Validate Accuracy Tables` (uses `--skip-freshness`), `Audit Website Supabase Tables` (uses `--skip-accuracy`), and `Enforce Supported Model Freshness` (exits early)
  - the signal uses default-true semantics: the workflow writes `true` before running backtest, and each model call only writes `false` when it finds new shows. This ensures correct AND behavior when notebook and deal produce different results
  - missing supported-model rows count as stale, not as pass
- The workflow summary shows per-band health, execution mode, missing-setlist counts, prediction handling, and supported-model freshness.
- GitHub Actions YAML is the canonical daily workflow contract. Local Python helpers mirror it for operator convenience, but do not override it.

---

## Fantasy Goose

Automatically plays Fantasy Goose using JamBandNerd notebook predictions for Goose.

- **Triggers**:
  - `workflow_run`: After a `Daily Data Pipeline` run on `main` completes (any conclusion). A gate job downloads the `band-status-goose` artifact and checks that Goose predictions were freshly generated (`prediction_action == "generated"`) before proceeding.
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
- The workflow installs browsers through `uv run python -m playwright ...`, matching the Python runtime dependency that powers the automation code.
- Playwright browser binaries are cached in `~/.cache/ms-playwright`; OS dependencies are still installed per run because they are runner-level packages rather than cacheable repo artifacts.

---

## Sync Retained Prediction Corpus

Regenerates the retained last-50 completed-show prediction and accuracy corpus for one or more bands. This is the canonical way to backfill website-facing prediction and accuracy data.

- **Triggers**: `workflow_dispatch` only
- **Inputs**: `band` (all or specific), `dry_run` (boolean)
- **Flow**:
  1. Setup job resolves the band list from `scripts/get_all_bands.py` (or uses the selected band)
  2. Per-band job runs `scripts/sync_retained_prediction_corpus.py --band <band> --window 50 --no-incremental` to recompute and prune the retained corpus across all pipeline-enabled models
  3. Per-band validation runs `scripts/validate_accuracy_tables.py --band <band> --skip-freshness`
  4. Summary job writes results
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
  1. Set up Python 3.12 + uv and Node 22
  2. `npm run verify:python`
  3. `python scripts/check_version_sync.py`
  4. `npm run verify:docs`
  5. `npm run verify:clean`

---

## Website Quality

CI quality gate for the `apps/web` Next.js website.

- **Triggers**: `pull_request` and `push` to `main`
- **Steps**:
  1. Set up Node 22 + `npm ci`
  2. Install Playwright OS dependencies and cache Chromium browser binaries
  3. `npm run verify:web`
  4. `npm run verify:clean`

---

## Hosted Website Smoke

Daily smoke test against the live deployed website.
The canonical production URL is `https://jambandnerd.com`.

- **Triggers**:
  - `schedule`: `0 22 * * *` (daily at 22:00 UTC)
  - `workflow_dispatch` with input: `base_url` (default `https://jambandnerd.com`)
- **Steps**: Runs `npm run test:web:smoke:hosted` with Playwright Chromium
- Browser binaries are cached in `~/.cache/ms-playwright`; OS dependencies are installed per run.
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
- `scripts/check_supported_model_freshness.py` — audit supported prediction and accuracy freshness without failing before status artifacts are written
- `scripts/rebuild_derived_data.py` — rebuild predictions and accuracy after schema changes
- `scripts/generate_live_predictions.py` — write active next-show predictions into `next_show_prediction_runs` and `next_show_prediction_songs`
- `scripts/sync_retained_prediction_corpus.py` — write and prune the active last-50 completed-show corpus in `completed_show_prediction_runs` and `completed_show_accuracy`
- `scripts/wipe_band_data.py` — clear derived outputs per band/model
