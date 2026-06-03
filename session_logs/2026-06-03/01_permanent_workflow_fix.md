# Session Log: Permanent Daily Workflow Fix

Date: 2026-06-03
Branch: `main` (needs feature branch per AGENTS.md rule 6)

## Goal

Fix two workflow failures permanently:

1. **Weekly Correction Sweep**: UM sweep's `Setup Sweep Parameters` failed because `date -u +%H` returned 20 instead of 19 (runner delayed by queue contention with the daily pipeline at 19:00 UTC).
2. **Daily Pipeline (Billy)**: Accuracy staleness enforcement produced misleading errors when collection failed (said "regeneration completed" when collection had actually failed). Root cause: non-WSP retry loop didn't write failure outputs, and Enforce step didn't distinguish collection failure from regeneration staleness.

## Constraints

- Never work directly on `main`
- Minimal diff
- Preserve existing workflow contracts

## Root Causes

### Weekly Correction Sweep (Run #26844944575)
- All 6 cron schedules trigger the same workflow
- Band selection used `date -u +%H` to map current hour to a band
- When runner started at 20:05 UTC (scheduled for 19:00), hour 20 had no mapping
- Daily pipeline also runs at 19:00 UTC — on Tuesdays both workflows compete for runners

### Daily Pipeline (Run #26779931900 — Billy, Jun 1)
- PR #160 fixed the `ensure_source_reachable` 15s hardcoded timeout (now uses config.timeout)
- But the non-WSP retry loop didn't write `workflow_state=failed` outputs before `exit 1`
- Downstream Enforce step couldn't tell collection failed vs. regeneration completed
- Reported "regeneration completed but accuracy remained stale" when collection had actually failed

## Files Changed

- `.github/workflows/weekly-correction-sweep.yml` — Replace `date -u +%H` with `github.event.schedule` cron parsing for band selection
- `.github/workflows/daily-pipeline.yml` — Non-WSP retry loop writes failure outputs; Enforce step skips staleness enforcement when `WORKFLOW_STATE == "failed"`
- `docs/operations/github_actions.md` — Updated failure policy and correction sweep sections

## Fix Details

### Fix 1: Correction Sweep Band Selection
```yaml
# Before: fragile to runner delays
CURRENT_HOUR=$(date -u +%H)
case $CURRENT_HOUR in
  19) BAND="um" ;;

# After: uses intended schedule time, not wall clock
SCHEDULED_HOUR=$(echo "${{ github.event.schedule }}" | awk '{print $2}')
case $SCHEDULED_HOUR in
  19) BAND="um" ;;
```
`github.event.schedule` contains the cron string that triggered the run (e.g. `"0 19 * * 2"`). Extracting hour from the cron is immune to runner startup delays.

### Fix 2: Daily Pipeline Retry Loop + Enforce Step
- Non-WSP retry loop: writes `workflow_state=failed`, `outcome_code=failed`, `prediction_action=skipped`, `recent_data_usable=false` before `exit $FINAL_EXIT_CODE`
- Enforce step: adds early-exit when `WORKFLOW_STATE == "failed"` — issues `::warning::` instead of `::error::` since predictions/accuracy were expected to be stale after a collection failure. The collection failure itself remains the primary error.

## Verification

- `tests/test_daily_workflow_contract.py` — 4/4 passed
- `tests/pipeline/test_band_collection_regressions.py` — 4/4 passed
- `tests/test_data_diagnostics_scripts.py` — 10/10 passed
- `npm run verify:docs` — passed

## Next Step

Monitor the next scheduled Weekly Correction Sweep (2026-06-09) to confirm UM sweep runs at hour 19 without the hour-20 misroute. Also monitor Daily Pipeline to confirm no stale-accuracy false errors when non-WSP collection fails.

