# Session 2026-05-03/01 — Daily Workflow Degraded Freshness Fix

## Goal

Fix the daily pipeline so degraded bands (e.g. WSP with EC unreachable) don't hard-fail on stale prediction freshness enforcement. Also PR site changes (PLAYBOOK lessons + next-env.d.ts).

## Root Cause

The `Enforce Supported Model Freshness` step in `daily-pipeline.yml:554-561` treated "degraded + stale" predictions identically to "normal + stale": `::error::` + `exit 1`. When WSP is degraded (EC unreachable), predictions can't be regenerated, so they naturally go stale after 48h. The enforce step should warn, not error, when the band is already known to be degraded.

PR #91 (`dev` branch, "Harden daily pipeline stale-data handling") added `missing_data` guards but didn't fix the enforce step.

## Changes

### PR #91 (merged)

- **`.github/workflows/daily-pipeline.yml`**: Changed `Enforce Supported Model Freshness` step to use `::warning::` instead of `::error::` when `WORKFLOW_STATE == "degraded"`, and skip `exit 1` so the pipeline completes with warnings
- Resolved merge conflict in `src/jambandnerd/data_collection/wsp/status.py` (dev + main merge)
- Fixed black formatting in WSP test files

### PR #100 (merged)

- **`.agent/PLAYBOOK.md`**: Added two playbook lessons from the WSP hotfix (PR #93):
  - Test fallback scraper detection guards against real single-set/festival formats
  - Test degraded paths in CI, not just locally; check which branch CI runs

### PR #99 (closed)

- Dependabot eslint 9→10 bump blocked by `eslint-plugin-react` incompatibility (`contextOrFilename.getFilename is not a function`)

## Commands Run

```bash
npm run verify:python   # 396 passed, 6 skipped, lint clean
gh pr checks --watch    # Repo Quality + Website Quality both green
```

## Validation Status

- `npm run verify:python`: 396 passed, 6 skipped
- CI: Repo Quality pass, Website Quality pass
- PR #91 merged: https://github.com/connorkitchings/JamBandNerd/pull/91
- PR #100 merged: https://github.com/connorkitchings/JamBandNerd/pull/100
- PR #99 closed (blocked upstream)

## Next Step

- Run daily pipeline via `workflow_dispatch` on main to verify WSP degraded mode completes with warnings instead of errors
