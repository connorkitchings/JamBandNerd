# 2026-03-20 Session Log 06

## Goal

Implement the operational recovery plan that keeps raw data by default, audits
bands first, and rebuilds only derived prediction and accuracy outputs after
the normalization and `show_id` contract changes.

## Changes Made

### Raw-data audit workflow

**New file:** `scripts/audit_raw_data.py`

- Added a simple operational entrypoint for auditing one band or all supported
  bands
- Reused `scripts.diagnose_band_data.diagnose_band()` rather than creating a
  second audit implementation
- Returns a non-zero exit when any selected band has raw-data issues

### Derived-data rebuild workflow

**New file:** `scripts/rebuild_derived_data.py`

- Added a band-by-band rebuild entrypoint for:
  - predictions
  - `accuracy_per_show`
  - aggregate accuracy tables
- Supports targeted recovery controls:
  - `--band`
  - `--clear-existing`
  - `--skip-predictions`
  - `--skip-accuracy`
  - `--start`
  - `--end`
  - `--recent-shows`
- Reuses existing scripts and contracts rather than introducing a new pipeline
  path
- Validates prediction freshness after prediction rebuilds

### Backtest support

**Modified:** `scripts/run_backtest.py`

- Added `--all-history` so recovery workflows can rebuild full per-show
  accuracy history without manufacturing a date window

### Documentation

**New file:** `docs/operations/data_recovery_rebuild.md`

- Added a runbook for:
  - auditing raw tables
  - applying the `accuracy_per_show.show_id` migration
  - rebuilding derived outputs band by band

**Modified:**

- `mkdocs.yaml`
- `docs/operations/github_actions.md`
- `scripts/README.md`

These now point to the manual audit/rebuild workflow and the new scripts.

### Tests

**New file:** `tests/test_operational_recovery_scripts.py`

Coverage added for:

- audit summary/failure counting
- per-band rebuild orchestration
- prediction-validation skipping when predictions are skipped
- derived-output clearing against the selected tables/models

## Validation

- `uv run pytest -q tests/test_operational_recovery_scripts.py tests/test_data_diagnostics_scripts.py tests/pipeline/test_run_backtest.py tests/pipeline/test_run_optimized_pipeline.py`
  passed
- `uv run ruff check scripts/audit_raw_data.py scripts/rebuild_derived_data.py scripts/run_backtest.py tests/test_operational_recovery_scripts.py`
  passed
- `uv run --with mkdocs --with mkdocs-material --with pymdown-extensions mkdocs build --strict`
  passed

## Operational Follow-Up

- The live Supabase migration still needs to be applied manually:
  `supabase/migrations/20260322_accuracy_per_show_show_id_text.sql`
- The new rebuild script should then be run against the real database to
  regenerate:
  - `accuracy_per_show`
  - `notebook_accuracy`
  - `accuracy_ckplus`
  - optional fresh prediction rows
