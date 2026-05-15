# Pre-Merge Data Audit Repairs

## Goal

Clear pre-merge main/dev audit blockers for the six-band legacy production
tables before opening `feat/single-model-per-band` to `dev`.

## Constraints

- Audit only the legacy `main`/`dev` production contract, not feature-branch
  `setlist_*` promotion tables.
- Use `/private/tmp/jbn-main-audit` and `/private/tmp/jbn-dev-audit` so the
  feature branch remains isolated from branch-specific repair commands.
- Repair raw data only through existing collectors; no manual setlist inserts
  or fallback parser additions.
- Regenerate historical predictions through normal backtest upsert paths so
  saved rows reflect the corrected algorithm at each reference date.

## Changes Made

- Fixed UM source preflight so `ensure_source_reachable("um")` probes the
  concrete AllThings setlist API endpoint instead of the API root.
- Fixed Notebook prediction filtering so band-specific excluded songs are
  removed before the final `top_k` slice, preserving 50 eligible WSP Notebook
  predictions when `Drums` ranks inside the raw top 50.
- Added focused regression tests for both fixes.
- Mirrored the UM and WSP code patches into `/private/tmp/jbn-dev-audit` for
  Supabase repair runs.

## Data Repairs

- Re-ran targeted UM collection for 2026-05-01 through 2026-05-04; raw setlists
  for UM shows `1773756273` and `1773756291` were collected through the existing
  API collector.
- Re-ran UM Notebook and Deal retained-window backtests after the new setlists
  entered the 50-show replay window.
- Re-ran WSP Notebook retained-window backtest after the Notebook top-k fix,
  regenerating 50 historical prediction and accuracy rows through normal
  upsert paths.

## Validation

Commands run and focused code checks passed:

```bash
uv run pytest -q tests/test_data_diagnostics_scripts.py
uv run ruff check scripts/common.py tests/test_data_diagnostics_scripts.py
uv run pytest -q tests/models/test_notebook_model.py
uv run ruff check src/jambandnerd/models/notebook/model.py tests/models/test_notebook_model.py
```

Supabase repair and validation commands passed:

```bash
uv run python scripts/run_um_collection.py --start-date 2026-05-01 --end-date 2026-05-04 --full-backfill
uv run python scripts/run_backtest.py --band um --model notebook --shows 50 --no-incremental
uv run python scripts/run_backtest.py --band um --model deal --shows 50 --no-incremental
uv run python scripts/run_backtest.py --band wsp --model notebook --shows 50 --no-incremental
uv run python /private/tmp/jbn_legacy_30day_audit.py --worktree /private/tmp/jbn-dev-audit --branch-label dev --start 2026-04-14 --end 2026-05-13 --output-dir /private/tmp/jbn-audit-reports
uv run python /private/tmp/jbn_legacy_30day_audit.py --worktree /private/tmp/jbn-main-audit --branch-label main --start 2026-04-14 --end 2026-05-13 --output-dir /private/tmp/jbn-audit-reports
uv run python scripts/validate_accuracy_tables.py --max-age-hours 72 --replay-window 50
uv run python scripts/audit_supabase_tables.py --max-age-hours 72
```

Both `/private/tmp/jbn-main-audit` and `/private/tmp/jbn-dev-audit` 30-day
legacy audits now report zero blockers. Billy remains warning-only for
documented upstream source gaps.

Commit hook note: `git commit` could not run the local hook because
`pre-commit` is not installed in this environment, and `uv run pre-commit`
could not access the user uv cache from the sandbox. Focused pytest/ruff and
Supabase validations above were run directly.

## Artifacts

- `/private/tmp/jbn-audit-reports/main_legacy_30day_audit.json`
- `/private/tmp/jbn-audit-reports/main_legacy_30day_audit.md`
- `/private/tmp/jbn-audit-reports/dev_legacy_30day_audit.json`
- `/private/tmp/jbn-audit-reports/dev_legacy_30day_audit.md`
- `/private/tmp/jbn-audit-reports/pre_merge_main_dev_audit_final.md`

## Files Changed

- `scripts/common.py`
- `src/jambandnerd/models/notebook/model.py`
- `tests/models/test_notebook_model.py`
- `tests/test_data_diagnostics_scripts.py`
- `session_logs/2026-05-14/02_premerge_data_audit_repairs.md`

## Next Step

Open the `feat/single-model-per-band` PR to `dev`; the final audit report now
recommends go with Billy retained as warning-only upstream source availability.
