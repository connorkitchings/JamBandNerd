# Session Log: Daily Pipeline Timeout Fix and Workflow Health Review

Date: 2026-06-02
Branch: `main` (merged from `dev`)

## Goal

Review and address failures in the daily/weekly GitHub Actions workflows, specifically the Billy Strings timeout failure in the Daily Data Pipeline.

## Constraints

- Never work directly on `main` (used `dev` branch, PR #160)
- Preserve existing CollectorConfig contracts
- Minimal diff

## Commands Run

```bash
gh run list --workflow="Daily Data Pipeline" --limit 10
gh run list --workflow="Weekly Correction Sweep" --limit 10
gh run list --workflow="Dependency Audit" --limit 5
gh run list --workflow="Repo Quality" --limit 5
gh run view 26779931900 --json jobs
gh run view 26779931900 --job=78941384285 --log
uv run pytest tests/test_data_diagnostics_scripts.py -v -k "ensure_source_reachable"
uv run pytest tests/pipeline/test_band_collection_regressions.py -v
gh workflow run daily-pipeline.yml --ref dev -f band=billy
gh pr checks 160
```

## Files Changed

- `scripts/common.py` — `ensure_source_reachable` now defaults to the band's `CollectorConfig.timeout` instead of a hardcoded 15 seconds.

## Artifacts

- PR #160: `fix(ci): daily pipeline timeout & production hardening` (merged to `main`)
- Manual Billy pipeline run on `dev`: ✅ success (run 26836820368)
- Previous daily pipeline runs: #418 (May 31) success, #419 (Jun 1) failure

## Issues Discovered & Resolved

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Daily pipeline #419 failed on Billy Strings | `ensure_source_reachable` hardcoded 15s timeout; Billy config specifies 120s; bmfsdb.com was slow and timed out on all 3 retries | Changed default timeout to `config.timeout` so each band's configured timeout is respected |

## Verification

- `tests/test_data_diagnostics_scripts.py` — 3/3 passed
- `tests/pipeline/test_band_collection_regressions.py` — 4/4 passed
- Manual Billy daily-pipeline run on `dev` — completed successfully
- PR #160 checks: Repo Quality ✅, Verify Website ✅, GitGuardian ✅, Vercel ✅

## Next Steps

- Monitor the next scheduled Daily Data Pipeline run (#420, expected 2026-06-02 19:00 UTC) to confirm Billy passes on `main`.
- Consider adding degraded-mode handling to Billy collection (similar to WSP) if bmfsdb.com reliability degrades further.
