# Incremental Backtest Freshness Gate

**Goal:** Fix the daily pipeline false-positive failures caused by a design conflict between incremental backtest optimization and 48h accuracy freshness enforcement.
**Constraints:** Preserve prediction freshness enforcement; only relax accuracy staleness when the backtest confirms all shows in the window are already scored.
**Validation Status:** 327 tests pass, `verify:python` and `verify:docs` green.

## Actions Taken

- Diagnosed the Apr 21 scheduled daily pipeline failure: billy, phish, um, eggy failed the `Enforce Supported Model Freshness` step because incremental mode skipped all already-scored shows (0 new), accuracy rows were not re-written, and `evaluated_at` timestamps aged past 48h.
- Confirmed goose/wsp passed because they had 1+ new shows in the window that refreshed accuracy timestamps.
- Confirmed two prior PR failures on dev (test `fetch_scored_show_ids` monkeypatch gap, black formatting) were already fixed in commits `ccdd002` and `79b5b2f` but not yet merged to main.
- Added `_write_github_output()` to `scripts/run_backtest.py` that writes `backtest_incremental_all_scored=true` when all shows are already scored, and `false` when new shows are found or incremental mode is off.
- Added gate to `Enforce Supported Model Freshness` step in `daily-pipeline.yml`: when `BACKTEST_INCREMENTAL_ALL_SCORED == "true"` and predictions are fresh, accuracy staleness is expected and enforcement is skipped.
- Prediction freshness is always enforced regardless of backtest state.
- Added 3 regression tests: true output, false output, no-output when GITHUB_OUTPUT env not set.
- Fixed black formatting and unused import from prior commits.

## Key Outcome

The daily pipeline will no longer fail for bands that have no recent shows. When incremental mode correctly identifies all shows as already scored, accuracy staleness is tolerated because the scores are immutable and correct. Prediction freshness enforcement is unaffected.

## Commands Run

```bash
gh run list --limit 20
gh run view 24742083477 --log-failed
gh run view 24742083477 --log
npm run verify:python
npm run verify:docs
```

## Files Changed

- `scripts/run_backtest.py` — GHA output emission
- `.github/workflows/daily-pipeline.yml` — enforcement gate
- `tests/pipeline/test_run_backtest.py` — 3 new tests
- Formatting fixes in 4 files from prior commits

## Next Step

- Merge `dev` to `main` to ship the freshness gate fix, the test monkeypatch fix, and the formatting fix.
- Verify the next scheduled daily pipeline run clears all bands.
