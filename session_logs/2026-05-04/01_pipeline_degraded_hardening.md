# Session 2026-05-04/01 — Pipeline Degraded-Mode Hardening

## Goal

Fix remaining daily pipeline failures for degraded bands (WSP, UM, Billy) where stale-data enforcement and Supabase audits treated expected staleness as hard failures.

## Root Cause Analysis

Three distinct issues discovered through iterative pipeline runs:

1. **WSP scraping future dates** — `collect_shows()` scraped entire tour pages for the current year (2026) with no `show_date > date.today()` filter, wasting requests on setlist pages for shows months in the future.

2. **UM/Billy upstream 500s hard-failing** — Non-WSP collection retry loop had no degraded-state detection. When upstream APIs returned persistent 500 errors, the script crashed with `RuntimeError` and the shell loop hard-failed after 3 retries.

3. **WSP stale enforcement bypassed** — After PR #91's `ensure_source_reachable` change (403 → warning instead of exception), WSP collection completed "successfully" with `workflow_state=success` even though recent setlist data was missing. The `Enforce Supported Model Freshness` and `Audit Website Supabase Tables` bash steps only checked the raw `steps.collection.outputs.workflow_state` — missing the `missing_data` flag that the `Write Band Status` Python step correctly used to override to `degraded`.

## Changes

### PR #102 (merged) — Collection fixes

- `src/jambandnerd/data_collection/wsp/collector.py`: Skip future shows (`show_date > date.today()`) during tour page scraping
- `scripts/run_um_collection.py`, `scripts/run_billy_collection.py`: Added `_emit_github_output()` helper and try/except around `ensure_source_reachable()` — on `RuntimeError`, emit `workflow_state=degraded` to GITHUB_OUTPUT, then re-raise
- `.github/workflows/daily-pipeline.yml`: Non-WSP retry loop now captures GITHUB_OUTPUT from the script (like WSP already does) and detects `workflow_state=degraded` → warns instead of hard-failing

### PR #103 (merged) — Supabase audit skip-accuracy for degraded

- `.github/workflows/daily-pipeline.yml`: Pass `--skip-accuracy` to `audit_supabase_tables` when `WORKFLOW_STATE == "degraded"`

### PR #104 (merged) — Audit --degraded flag for prediction staleness

- `scripts/audit_supabase_tables.py`: Added `--degraded` CLI flag and `degraded` parameter through `_derive_model_audit` → `run_supabase_audit`. When true, `canonical_predictions_stale` and `supported_prediction_freshness_stale` go to warnings instead of blockers
- `.github/workflows/daily-pipeline.yml`: Pass `--degraded` when `WORKFLOW_STATE == "degraded"`

### PR #105 (merged) — missing_data as degraded in enforce/audit steps

- `.github/workflows/daily-pipeline.yml`: Both `Enforce Supported Model Freshness` and `Audit Website Supabase Tables` steps now check `missing_data` in their `WORKFLOW_STATE` expression: `(steps.data_check.outputs.missing_data == 'true' && 'degraded') || <existing chain>`

### PR #99 (closed)

- Dependabot eslint 9→10 bump blocked by `eslint-plugin-react` incompatibility

## Commands Run

```bash
npm run verify:python   # 402 passed, 6 skipped
gh pr checks --watch    # All CI green for PRs #102-#105
```

## Validation Status

- `npm run verify:python`: 402 passed, 6 skipped
- CI: Repo Quality + Website Quality pass on all PRs
- Daily pipeline runs still had WSP failures after PRs #102-#104 — root-caused to `missing_data` gap in enforce/audit WORKFLOW_STATE, fixed in PR #105

## Next Step

- Run daily pipeline via `workflow_dispatch` on main to verify all bands complete (WSP with warnings only, not errors)
