# Session Log: WSP Daily Workflow Upstream-Lag Fix

Date: 2026-06-15
Branch: `fix/wsp-upstream-lag-degraded` (off `main`)

## Goal

Fix the recurring WSP daily-pipeline failure observed on run #27509635859 (2026-06-14) where a recent completed-show setlist gap (WSP show 22464, 2026-06-13) caused `outcome_code=failed_upstream_stale` and failed the whole job after 3 retries.

## Constraints

- Never work directly on `main` (per AGENTS.md rule 6).
- Preserve existing hard-failure contracts for collector regressions and true EC blocking.
- Distinguish "EC hasn't published yet" (upstream lag) from "EC blocked us" (request failure).
- No manual data backfill — rely on the probe + policy fix to degrade gracefully.

## Root Causes

### Run #27509635859 failure chain
1. WSP played 2026-06-13. The 2026-06-14 19:00 UTC daily pipeline ran first after that show.
2. `WSPCollector._scrape_single_setlist` fetched `20260613a.asp` via Playwright (Cloudflare bypass) but the page had no set markers → empty setlist.
3. `tourwrangler_fallback()` tried PanicStream + TourWrangler → both empty.
4. `classify_missing_recent_setlists()` re-probed EC to classify the gap and returned `ec_request_failed`.
5. `status.outcome_code()` → `failed_upstream_stale` → `workflow_state="failed"` → `RuntimeError`.
6. Workflow retried 3×; each retry hit the same diagnosis; pipeline failed.

### Bug #1 — probe mis-routes requests in CI
`_probe_everydaycompanion_setlist_status` (`orchestration.py:85`) used `session.get(...)` directly. The real collector uses `make_request()` / `make_simple_request()`, which route through `CloudflareBypass.make_request()` (Playwright) in CI. So in CI the probe was 403'd by EC and mis-classified every page-missing case as `ec_request_failed` even when the actual collector had just fetched the page successfully.

### Bug #2 — outcome policy was too coarse
`CollectionStatus.outcome_code()` mapped **both** `request_blocked_missing_setlists` *and* `upstream_missing_setlists` to `failed_upstream_stale`. So even with a correct diagnosis (page loads, no setlist yet), yesterday's-show-not-yet-on-EC failed the whole pipeline. The ops doc explicitly said "Recent completed-show setlist gaps from upstream blocking remain hard failures."

## Files Changed

- `src/jambandnerd/data_collection/wsp/orchestration.py`
  - `_probe_everydaycompanion_setlist_status` now uses `make_simple_request(session, url, allow_redirects=True)` so the probe rides the same Playwright-backed path as the collector in CI. Import added.
- `src/jambandnerd/data_collection/wsp/status.py`
  - `outcome_code()` splits the policy:
    - `collector_missing_setlists > 0` → `failed_internal` (hard fail, unchanged)
    - `request_blocked_missing_setlists > 0` → `failed_upstream_stale` (hard fail, unchanged)
    - `upstream_missing_setlists > 0` OR `fallback_available_missing_setlists > 0` → **new** `degraded_upstream_lag` (degrade)
    - `_has_systemic_http_failure()` → `degraded_upstream_blocked` (unchanged)
    - else → `success` (unchanged)
  - `workflow_state()` already returns `"degraded"` for any `degraded_*` outcome, so this flows through naturally and the workflow will reuse fresh prior predictions within the 48h freshness window.
- `docs/operations/github_actions.md`
  - Updated "WSP Degraded-Mode Handling" and "Failure Policy" to document the new `degraded_upstream_lag` outcome and the distinction between EC blocking (hard fail) vs EC lag (degraded).
- `tests/data_collection/wsp/test_status.py`
  - Added `test_upstream_missing_recent_setlist_is_degraded_lag`
  - Added `test_fallback_available_recent_setlist_is_degraded_lag`
  - Added `test_request_blocked_takes_precedence_over_upstream_missing` (mixed diagnoses still hard-fail)
- `tests/data_collection/test_wsp_orchestration.py`
  - Added `test_probe_everydaycompanion_routes_through_make_simple_request` — verifies the probe calls `make_simple_request` (the Playwright-backed path) rather than a direct `session.get`.
  - Added `test_probe_everydaycompanion_returns_ec_request_failed_on_requestexception` — verifies the `RequestException` branch still surfaces `ec_request_failed` so true blocking remains a hard failure.

## Commands Run

```bash
gh run list --workflow="Daily Data Pipeline" --limit 10
gh run view 27509635859 --json jobs
gh run view 27509635859 --job=81307229462 --log
uv run pytest tests/data_collection/wsp/test_status.py tests/data_collection/test_wsp_orchestration.py tests/test_daily_workflow_contract.py tests/pipeline/test_band_collection_regressions.py -v
uv run pytest tests/data_collection -q
uv run pytest tests/test_daily_workflow_contract.py tests/test_generate_pipeline_summary.py -q
uv run black --check src tests scripts && uv run ruff check src tests scripts
npm run verify:docs
```

## Validation

- 104/104 `tests/data_collection` pass
- 4/4 `tests/test_daily_workflow_contract.py` pass (including the docs contract check that now must reference the new failure-policy split)
- 4/4 `tests/pipeline/test_band_collection_regressions.py` pass
- 7/7 `tests/test_generate_pipeline_summary.py` pass
- `black --check` clean
- `ruff check` clean
- `npm run verify:docs` builds MkDocs successfully

## Expected Behavior After Merge

- Next WSP daily run: if EC still hasn't published the 2026-06-13 setlist, the probe will now correctly return `upstream_missing_setlist` (because it uses Playwright in CI). `outcome_code()` returns `degraded_upstream_lag`, the band job degrades instead of failing, predictions are reused within the 48h freshness window, and the missing show will age out of the `WSP_BACKUP_WINDOW_DAYS=3` recent window around 2026-06-16.
- If EC actually blocks us (true `RequestException`), `outcome_code()` still returns `failed_upstream_stale` and the pipeline hard-fails as before.

## Next Step

- Merge the PR and monitor the next scheduled Daily Data Pipeline run (2026-06-15 19:00 UTC) to confirm WSP degrades rather than fails.
- If EC later publishes the 2026-06-13 setlist, a subsequent run will collect it normally via the bounded refresh path.
