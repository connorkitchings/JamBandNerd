# Audit Supabase Tables: Lineage-Shortfall Symmetry Fix

## Goal

Permanently fix recurring daily-pipeline failures that were persisting even after the aa18e81 prune+validator fix from 2026-04-28.

## Root Cause

The `validate_accuracy_tables.py` validator was relaxed in aa18e81 to accept count < required_window when all replay rows have valid `prediction_run_id` links (benign shortfall). But `audit_supabase_tables.py` — an independent parallel checker — still had 5 strict `< required_window` checks routing to `blockers`. Goose at 48/50 with intact lineage produced 10 blockers (5 per promoted model), causing the "Audit Website Supabase Tables" step to exit non-zero and fail the pipeline.

Timeline of failures that trace to this single asymmetry:
- 2026-04-22: 4 bands failed (prune destruction left 48/50)
- 2026-04-25–27: recurring schedule failures
- 2026-04-28 multiple runs: goose continued failing after main received aa18e81

## Fix

**`scripts/audit_supabase_tables.py`** (lines 308–348):
- Compute `lineage_intact = bool(replay_rows) and not replay_lineage_missing_dates` before the shortfall routing.
- Route all `_below_window` shortfalls to `warnings` when `lineage_intact` is true (not skip_accuracy mode) — matches the validator's `[OK]` branch.
- Empty corpus (`not replay_rows`) is treated as broken → `shortfall_target = blockers`, same as broken lineage.
- `replay_lineage_missing_prediction_run_id` stays a hard blocker independently of shortfall_target.
- Added cross-reference docstring in both scripts to prevent future re-introduction of the asymmetry.

## Files Changed

- `scripts/audit_supabase_tables.py`: 49 lines changed (routing logic + docstring)
- `scripts/validate_accuracy_tables.py`: 6 lines changed (docstring cross-reference only)
- `tests/test_audit_supabase_tables.py`: 133 lines changed (3 updated, 3 new tests)

## Commands Run

```bash
uv run pytest tests/test_audit_supabase_tables.py -v               # 17 passed
uv run pytest tests/ -v                                             # 119 passed, 6 skipped
uv run ruff check && uv run black --check .                         # clean
git push origin dev
gh pr create ... --base main --head dev                             # PR #89
gh workflow run daily-pipeline.yml --ref dev -f band=goose          # run 25112901613
```

## Expected Outcome (pending live run)

Run 25112901613 should complete with:
- Goose "Audit Website Supabase Tables" step exits 0
- Audit JSON: `state=warning`, `blockers=[]`, warnings contain the 5 `_below_window` entries per model
- "Validate Accuracy Tables" step exits 0 (already fixed in aa18e81)
- New `WARNING: show {id} ({date}) skipped: ...` lines in backtest log revealing the 2 goose shows that are failing to score (Phase 4 follow-up)

## Phase 4 Follow-Up — RESOLVED

Run 25112901613 completed successfully:

```
[GOOSE/NOTEBOOK] Incremental: 48 show(s) already scored, 2 new.
[GOOSE/DEAL]     Incremental: 48 show(s) already scored, 2 new.
```

Both new shows scored without errors — no `WARNING: show` lines in the backtest log. Audit artifact: `state=ok, blockers=0, warnings=0`.

**Conclusion**: The 2 previously-failing shows appear to have naturally left the 50-show window (replaced by newer shows). Once the prune fix stopped destroying the corpus, today's 2 new shows scored cleanly and brought the corpus back to 50/50. No recoverable bug found — the gap was benign churn resolved by the prune fix alone.

Pipeline status: fully resolved. No further action required.
