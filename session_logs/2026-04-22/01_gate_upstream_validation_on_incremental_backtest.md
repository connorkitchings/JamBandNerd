# Gate Upstream Validation Steps on Incremental Backtest State

**Goal:** Fix two daily pipeline failure modes: (1) upstream validation/audit steps failing on stale accuracy timestamps when incremental backtest correctly skips all-scored shows, and (2) a latent two-model output overwrite bug in `backtest_incremental_all_scored`.
**Constraints:** Preserve prediction freshness enforcement; only relax accuracy staleness when the backtest confirms all shows in the window are already scored.
**Validation Status:** 331 tests pass, `verify:python` and `verify:docs` green.

## Actions Taken

- Diagnosed Apr 22 scheduled daily pipeline failure: phish, um, billy, eggy failed at `Validate Accuracy Tables` (72.2h > 72h) and `Audit Website Supabase Tables` (stale accuracy as blocker). Goose and wsp passed because they had new shows that refreshed timestamps.
- Confirmed the Apr 21 `backtest_incremental_all_scored` gate fix was working for `Enforce Supported Model Freshness` but the two upstream steps were not gated.
- Added `--skip-freshness` flag to `validate_accuracy_tables.py` that skips the `evaluated_at` age check but still validates row presence, timestamp validity, and replay lineage.
- Wired `BACKTEST_INCREMENTAL_ALL_SCORED` env var into `Validate Accuracy Tables` (passes `--skip-freshness`) and `Audit Website Supabase Tables` (passes existing `--skip-accuracy`) in `daily-pipeline.yml`.
- Fixed two-model output overwrite bug: `run_backtest.py` no longer writes `backtest_incremental_all_scored=true` when all shows are scored. Instead the workflow writes the default `true` before running backtest, and each model call only writes `false` when it finds new shows. This ensures correct AND semantics — the signal is `true` only when both notebook and deal had all shows scored.
- Added 4 new tests for `--skip-freshness` and updated the existing `test_run_backtest_writes_github_output_true_when_all_scored` test to verify the script no longer overwrites the default.
- Updated `docs/operations/github_actions.md` to document the three-gate pattern and the default-true output semantics.

## Commands Run

```bash
gh run list --workflow=daily-pipeline.yml --limit 5
gh run view 24798287477 --json jobs
gh run view 24798287477 --log
gh run view 24742083477 --json jobs
gh run view 24742083477 --log
npm run verify:python
npm run verify:docs
```

## Files Changed

- `scripts/validate_accuracy_tables.py` — added `--skip-freshness` flag and `_validate_row_skip_freshness()` helper
- `scripts/run_backtest.py` — removed `_write_github_output("backtest_incremental_all_scored", "true")` at the all-scored early return
- `.github/workflows/daily-pipeline.yml` — wired `BACKTEST_INCREMENTAL_ALL_SCORED` into `Validate Accuracy Tables` and `Audit Website Supabase Tables`; added default `true` write before backtest calls
- `tests/test_validate_accuracy_tables.py` — 4 new tests for skip-freshness behavior
- `tests/pipeline/test_run_backtest.py` — updated all-scored test to verify no script-side output overwrite
- `docs/operations/github_actions.md` — documented three-gate pattern and default-true output semantics

## Next Step

- Merge to `main` to ship both fixes.
- Verify the next scheduled daily pipeline run clears all 6 bands.
