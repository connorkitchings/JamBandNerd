# WSP Notebook Top-K Audit Fix

**Goal:** Fix the remaining `wsp` daily workflow failure after the backtest timeout work by correcting the website Supabase audit contract for canonical prediction `top_k`.
**Constraints:** Preserve the existing workflow shape, keep the audit strict about real data inconsistencies, and avoid forcing a hard `50`-row invariant when canonical rows and projections are otherwise internally consistent.
**Validation Status:** Targeted audit and prediction validation tests passed locally in this session.

## Actions Taken
- Downloaded the failing `wsp` Supabase audit artifact from workflow run `24572559110` and confirmed the only blocker was `wsp:notebook:canonical_predictions_top_k_mismatch`.
- Verified the canonical `wsp/notebook` row was internally consistent at `top_k=49`, `projection_rows=49`, and matching top song, which showed the audit was enforcing the wrong invariant.
- Updated `scripts/audit_supabase_tables.py` so canonical prediction validation now enforces consistency between stored `top_k`, the canonical JSON payload length, and projection rows instead of requiring equality with the model registry default.
- Replaced the old top-k mismatch test with a regression test for the valid `49/49` case and added a new failure case for canonical payload/top-k inconsistency.

## Key Outcome
- The website-facing Supabase audit now matches how prediction rows are actually written by the generation and backfill paths. Legitimate reduced prediction sets no longer fail the daily pipeline, while real canonical/projection mismatches still block.

## Commands Run
- `gh run view 24572559110 --job 71849336101 --log-failed`
- `gh run download 24572559110 -n supabase-audit-wsp -D /tmp/jbn-run-24572559110`
- `uv run pytest -q tests/test_audit_supabase_tables.py`
- `uv run pytest -q tests/test_validate_prediction_tables.py`

## Files Changed Or Artifacts Produced
- Audit logic: `scripts/audit_supabase_tables.py`
- Regression tests: `tests/test_audit_supabase_tables.py`
- Downloaded debugging artifact: `/tmp/jbn-run-24572559110/wsp.json`
- Session artifact: `session_logs/2026-04-17/06_wsp_notebook_top_k_audit_fix.md`

## Next Step
- Re-run the daily workflow and confirm `wsp` clears the Supabase audit step with no regression on other bands.
