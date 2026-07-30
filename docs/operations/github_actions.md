# GitHub Actions

This repository uses 10 GitHub Actions workflows for pipeline automation, CI quality gates, and operational monitoring.

## Workflow Summary

| Workflow | File | Schedule | Manual | PR/Push | Bands |
|----------|------|----------|--------|---------|-------|
| Daily Data Pipeline | `daily-pipeline.yml` | 19:00 UTC daily | Yes | -- | Daily publishing bands |
| Weekly Correction Sweep | `weekly-correction-sweep.yml` | Tue 13:00-18:00 UTC staggered | Yes | -- | goose, phish, eggy, billy, wsp, um |
| Fantasy Goose | `fantasy-goose.yml` | After daily pipeline | Yes | -- | goose |
| Backfill Predictions | `backfill-predictions.yml` | -- | Yes | -- | Active model bands |
| Live Show Tracker | `live-tracker.yml` | -- | Yes | -- | goose, phish, wsp, billy, um |
| Repo Quality | `repo-quality.yml` | -- | -- | PR + push main | -- |
| Website Quality | `web-quality.yml` | -- | -- | PR + push main | -- |
| Hosted Website Smoke | `hosted-web-smoke.yml` | 22:00 UTC daily | Yes | -- | -- |
| Dependency Audit | `dependency-audit.yml` | Mon 14:00 UTC | Yes | -- | -- |
| Test Secrets | `test_secrets.yml` | -- | Yes | -- | -- |

---

## Weekly Correction Sweep

The weekly correction sweep runs automatically on Tuesdays staggered hourly by band:
- 13:00 UTC (9:00 AM ET) - Goose
- 14:00 UTC (10:00 AM ET) - Phish
- 15:00 UTC (11:00 AM ET) - Eggy
- 16:00 UTC (12:00 PM ET) - Billy Strings
- 17:00 UTC (1:00 PM ET) - Widespread Panic
- 18:00 UTC (2:00 PM ET) - Umphrey's McGee

The sweep completes by 19:00 UTC, avoiding queue contention with the daily pipeline at 19:00 UTC.
Band selection for scheduled runs uses the cron expression (`github.event.schedule`) rather than the current wall-clock time, so runner startup delays do not misroute bands.

It uses the `correction_detector.py` module to perform checksum-based comparison of stored DB raw records with fresh upstream data over a 730-day lookback window. Use `workflow_dispatch` for manual runs or repair validation.

---

## Daily Data Pipeline

The primary production workflow. Collects raw data, generates predictions, runs backtests, and validates freshness for the daily publishing bands.

- **Triggers**:
  - `schedule`: `0 19 * * *` (daily at 19:00 UTC / 3:00 PM ET during DST)
  - `workflow_dispatch` with inputs: `band` (`all` or a single band), `skip_accuracy` (boolean)

- **Steps per band** (parallel matrix):
  1. Compute collection preflight via `scripts/collection_preflight.py`
  2. Run data collection via `scripts/run_{band}_collection.py` (with retry logic)
  3. Verify data freshness via `scripts/verify_data_freshness.py`
  4. Generate live next-show predictions via `scripts/generate_live_predictions.py`
  5. Validate live prediction tables via `scripts/validate_prediction_tables.py`
   6. Sync the retained completed-show corpus via `scripts/sync_retained_prediction_corpus.py --window 50` (skippable via `skip_accuracy`; emits `backtest_incremental_all_scored` output through the underlying scorer)
  8. Validate accuracy tables via `scripts/validate_accuracy_tables.py` (passes `--skip-freshness` when all shows already scored)
  9. Audit supported-model freshness via `scripts/check_supported_model_freshness.py`
  10. Audit website Supabase tables via `scripts/audit_supabase_tables.py` (passes `--skip-accuracy` when all shows already scored)
  11. Write per-band status summary and enforce stale-freshness escalation after artifacts are uploaded

- **Band matrix**: Built by `scripts/get_all_bands.py`, which reads `get_daily_pipeline_bands()` from repo config. Eggy remains collectable but excluded from default daily publishing until promoted.
- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`; `PHISH_API_KEY` for Phish only.

### Bands With No Upcoming Show (Idle Predictions)

Collection is driven by recent activity (recent completed shows, missing recent setlists, or upcoming shows), so a band can legitimately have `should_run_collection=true` even when it has no upcoming show at all — for example, between tour legs.

- The preflight emits two distinct upcoming signals:
  - `has_upcoming_show_soon`: a show exists inside the `CollectionPolicy.upcoming_lookahead_days` window (default 14 days). Used for the **collection** execution-mode decision.
  - `has_upcoming_show`: a show exists on record **anywhere in the future**. Used to gate prediction generation.
- `Generate Predictions` and `Validate Prediction Tables` gate on `has_upcoming_show`. When a band has no future show on record, those two steps are **skipped** rather than failed. `scripts/generate_live_predictions.py --require-output` is never invoked without a target show, so it cannot raise `No upcoming show found`.
- UM's future shows live in the dedicated `um_upcoming_shows` table (Seated), since allthings.umphreys.com only archives played shows. The preflight's `has_upcoming_show` falls back to `um_upcoming_shows` for UM, mirroring `scripts/validate_prediction_tables.py` and `scripts/generate_live_predictions.py`.
- The `Run Backtest and Save Per-Show Accuracy` step is intentionally **not** gated on upcoming shows, so per-show accuracy for completed shows is still regenerated and stays within the freshness window.
- The supported-model freshness auditor mirrors this: predictions are reported as fresh when no upcoming show exists, so staleness enforcement does not escalate.

### WSP Show Collection Window

- The default WSP collection window spans the prior year through **next year** (`default_wsp_year_window` in `scripts/run_wsp_collection.py`). This eliminates a Jan-1 blind spot where next year's tours would be invisible until New Year's Day.
- Everyday Companion typically does not publish `tour{YY+1}.asp` until late in the year; the collector treats an unpublished tour page (HTTP 404) as a soft skip and continues, so scanning next year is safe year-round.

### WSP Degraded-Mode Handling

- WSP installs Playwright (Firefox) for scraping reliability.
- Upstream blocking without recent completed-show gaps is treated as **degraded**.
- Degraded runs skip prediction/backtest regeneration and report whether the website is reusing prior data.
- WSP upstream blocking that leaves recent completed-show data unusable is a hard failure.
- The daily workflow now runs one registered model version per active band with strict output requirements. A supported model that exits without writing fresh predictions or per-show backtest rows is treated as a workflow failure instead of a silent success.
- Supported-model reuse during degraded mode is now bounded:
  - if reused prediction freshness stays within `48h`, the band can remain degraded but non-failing
  - if supported-model prediction freshness exceeds `48h`, the band job fails after the status artifact and summary are written
  - accuracy uses the same `48h` window, except manual `skip_accuracy=true` runs and WSP `degraded_upstream_lag` outcomes report stale immutable accuracy informationally until it can be regenerated
- The sampled 2026-04-13 WSP Notebook freshness gap should therefore be treated as a real operational defect that requires regeneration or workflow investigation, not as acceptable drift.
- Recent missing-setlist outcomes are split by diagnosis:
  - `failed_internal` — the collector saw a parseable EC setlist but did not store it (collector regression; hard fail).
  - `failed_upstream_stale` — the EC request itself failed (`ec_request_failed`, true bot blocking / network failure; hard fail).
  - `degraded_upstream_lag` — the EC page loaded cleanly via Playwright but the setlist is not published yet (`upstream_missing_setlist`) or only fallback data exists (`fallback_data_available`). This is upstream lag, not a system defect: the run degrades and reuses fresh prior predictions within the `48h` window. The missing show will age out of the `WSP_BACKUP_WINDOW_DAYS=3` recent window and recover naturally.

### Eggy Cloudflare Bypass

- Eggy (`thecarton.net`) is behind Cloudflare bot protection with JS challenges.
- The Eggy collector tries standard HTTP requests first; on 403 it falls back to Playwright (Firefox) via the shared `data_collection/browser.py` module.
- Playwright is installed in CI for both WSP and Eggy bands.
- Because browser-backed collection and automation import Playwright directly at runtime, it is a locked runtime dependency rather than a dev-only tool.
- If Cloudflare is lifted, Eggy automatically skips Playwright and uses direct HTTP.

### Failure Policy

- Non-WSP collection failures are hard failures. On failure, the collection step writes `workflow_state=failed` outputs so downstream steps can distinguish collection failure from regeneration staleness.
- WSP collector regressions are hard failures.
- WSP upstream blocking is degraded only when recent completed-show data is still usable.
- Recent completed-show setlist gaps are classified by the missing-setlist probe (`_probe_everydaycompanion_setlist_status` in `src/jambandnerd/data_collection/wsp/orchestration.py`):
  - `failed_internal` (collector saw the setlist but did not store it) — hard failure.
  - `failed_upstream_stale` (`ec_request_failed`: the EC request itself raised an exception, indicating bot blocking or network failure) — hard failure.
  - `degraded_upstream_lag` (`upstream_missing_setlist`: EC page loaded cleanly via Playwright but has no published setlist yet; or `fallback_data_available`) — degraded; the pipeline reuses fresh prior predictions within the `48h` window and recovers naturally once the show ages out of the `WSP_BACKUP_WINDOW_DAYS=3` recent window.
- Supported-model freshness is a separate enforcement path from collection success:
  - When collection itself fails, staleness enforcement is skipped (predictions and accuracy could not be regenerated this run).
  - degraded reuse older than `48h` is a hard failure for supported predictions
  - stale supported accuracy is a warning, rather than a failure, for a manual `skip_accuracy=true` run or WSP's explicit `degraded_upstream_lag` outcome; it remains visible in the status artifact and Supabase audit because it cannot be safely regenerated until the upstream setlist arrives
  - stale supported accuracy remains a hard failure for normal regeneration runs, collector regressions, and true upstream blocking
  - when incremental backtest finds all shows in the window already scored, accuracy staleness is expected and not enforced (scores are immutable; the backtest emits `backtest_incremental_all_scored=true`)
  - the `backtest_incremental_all_scored` signal gates three steps: `Validate Accuracy Tables` (uses `--skip-freshness`), `Audit Website Supabase Tables` (uses `--skip-accuracy`), and `Enforce Supported Model Freshness` (exits early)
  - the signal uses default-true semantics: the workflow writes `true` before running backtest, and the scorer writes `false` when it finds new shows
  - prediction freshness is always enforced regardless of backtest state
  - missing supported-model rows count as stale, not as pass
- The workflow summary shows per-band health, execution mode, missing-setlist counts, prediction handling, and supported-model freshness.
- GitHub Actions YAML is the canonical daily workflow contract. Local Python helpers mirror it for operator convenience, but do not override it.

---

## Fantasy Goose

Automatically plays Fantasy Goose using JamBandNerd's Goose prediction board.

- **Triggers**:
  - `workflow_run`: After a `Daily Data Pipeline` run on `main` completes (any conclusion). A gate job downloads the `band-status-goose` artifact and checks that Goose predictions were freshly generated (`prediction_action == "generated"`) before proceeding.
  - `workflow_dispatch` with inputs: `date` (YYYY-MM-DD), `dry_run` (boolean)

- **Behavior**:
  - Logs in to Fantasy Goose using stored credentials
  - Reads the authenticated show dropdown and song catalog
  - Selects the Goose show for the target date when the pick cutoff is open
  - Fetches Goose predictions for the exact `reference_date`
  - Maps the top 8 songs onto Fantasy Goose song ids and submits

- **Failure policy**:
  - `mapping_failed` or `missing_predictions` fails the workflow
  - `no_show_tonight`, `cutoff_passed`, `already_submitted`, and `dry_run` are non-error no-ops

- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `FG_USER_EMAIL`, `FG_PASSWORD`
- The workflow installs browsers through `uv run python -m playwright ...`, matching the Python runtime dependency that powers the automation code.
- Playwright browser binaries are cached in `~/.cache/ms-playwright`; OS dependencies are still installed per run because they are runner-level packages rather than cacheable repo artifacts.

---

## Backfill Predictions

Regenerates the retained completed-show corpus for one or more active model bands.

- **Triggers**: `workflow_dispatch` only
- **Inputs**: `band` (all or specific), `dry_run` (boolean)
- **Flow**:
  1. Setup job builds an active-band matrix
  2. Per-band backfill job runs `scripts/sync_retained_prediction_corpus.py --window 50 --no-incremental`
  3. The job validates retained accuracy with `scripts/validate_accuracy_tables.py --skip-freshness`
  4. Summary job writes results
- **Secrets**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

---

## Live Show Tracker

Tracks live shows by polling for setlist updates during a performance.

- **Triggers**: `workflow_dispatch` only
- **Inputs**: `band` (goose, phish, wsp, billy, um), `date` (YYYY-MM-DD), `interval` (default 60s), `max_iterations` (default 300), `bsky_handle` (WSP only)
- **Behavior**: Runs `scripts/run_live_tracker.py`, which polls upstream sources for setlist updates and publishes them. WSP polling uses the in-repo WSP parser directly (`src/jambandnerd/data_collection/wsp/parser.py`); the daily pipeline's Playwright-backed EC scraper is not invoked here, so the live tracker does not require a Playwright install step.
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

For implementation details, see the source of `scripts/run_{band}_collection.py`
and the shared validation helpers in `src/jambandnerd/db/`.

## Manual Recovery

For manual recovery or migration workflows:

- `scripts/audit_raw_data.py` — inspect raw data before targeted re-ingestion
- `scripts/check_supported_model_freshness.py` — audit supported prediction and accuracy freshness without failing before status artifacts are written
- `scripts/generate_live_predictions.py` — write active next-show predictions into `setlist_predictions` and `setlist_prediction_songs`
- `scripts/sync_retained_prediction_corpus.py` — write and prune the active last-50 completed-show corpus in `setlist_results` and `setlist_accuracy`
