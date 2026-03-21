# 2026-03-21 Session Log 03

## Goal
Audit the live Supabase production project against the current data strategy, harden the website read path around `prediction_songs`, and remediate any freshness or raw-data gaps that could be fixed safely from this session.

## What Changed
- Updated the website data layer to prefer `prediction_songs` for prediction payload reads, while retaining canonical `predictions_{model}` fallback behavior.
- Fixed the web Phish show ID mapping from `showid` to `api_show_id` so accuracy venue lookups align with the raw schema.
- Changed recent-accuracy reads in the website to resolve the current model version dynamically instead of hard-coding `${model}_v1`.
- Re-ran live collection for `eggy`, `um`, and `wsp`.
- Rebuilt derived outputs for `eggy` after raw-table recovery.
- Restored `um` derived outputs through a mixed recovery path after a network failure interrupted the full rebuild.

## Live Audit Results
- `scripts/validate_prediction_tables.py` initially passed for all bands/models; prediction freshness was healthy.
- `scripts/audit_raw_data.py --band all` initially found recent orphaned completed shows for `eggy`, `wsp`, and `um`.
- After recollection:
  - `eggy` raw data became clean.
  - `um` raw data became clean.
  - `wsp` still has one orphaned completed show on `2026-03-20` (`show_id=22455`) because the upstream Everyday Companion setlist page does not yet expose a setlist table.

## Commands Run
- `uv run python scripts/validate_prediction_tables.py`
- `uv run python scripts/audit_raw_data.py --band all`
- `npm run lint` (inside `apps/web`)
- `npm run build` (inside `apps/web`)
- `uv run python scripts/run_eggy_collection.py`
- `uv run python scripts/run_um_collection.py`
- `uv run python scripts/run_wsp_collection.py`
- `uv run python scripts/rebuild_derived_data.py --band eggy --clear-existing`
- `uv run python scripts/rebuild_derived_data.py --band um --clear-existing`
- `uv run python scripts/run_backtest.py --band um --model ckplus --shows 100`
- `uv run python scripts/save_aggregate_accuracy.py --band um --model notebook --shows 100`
- `uv run python scripts/save_aggregate_accuracy.py --band um --model ckplus --shows 100`
- `uv run python scripts/validate_prediction_tables.py --band eggy --band um`
- `uv run python scripts/audit_raw_data.py --band all`

## Verification Status
- Web lint passed.
- Web production build passed.
- Eggy predictions and projection rows were refreshed and validated.
- UM predictions, projection rows, and aggregate accuracy were restored and validated after the interrupted full rebuild.
- Final raw audit result: 5 bands clean, 1 band blocked by upstream WSP source lag.

## Risks / Follow-Up
- WSP remains partially stale for the `2026-03-20` show until Everyday Companion or the fallback source publishes a usable setlist.
- The full `um` rebuild command appeared to hang after partial progress; a narrower recovery path was used to restore the user-facing outputs. That command path should be reviewed for long-running or silent-stall behavior.
- During this session, unrelated working-tree changes appeared in other `apps/web` files outside the two files changed here. They were left untouched.
