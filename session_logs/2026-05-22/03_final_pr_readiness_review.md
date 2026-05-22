# Final PR Readiness Review — Live Rehearsal Fixes

## Goal

- Execute the final production PR readiness plan for `dev` before PR to `main`.
- Validate local quality gates, live Supabase state, frontend smoke coverage, and GitHub Actions readiness.

## Findings And Fixes

- Fixed retained backtest eligibility so partial same-day setlists are not treated as completed shows.
  - Root cause: Goose 2026-05-22 had only two collected songs, but `list_completed_shows()` selected it for the retained corpus.
  - Fix: `list_completed_shows()` now requires more than two unique songs, matching the scorer guard.
  - Regression: `tests/models/test_evaluation.py`.
- Fixed `scripts/sync_retained_prediction_corpus.py` after live rehearsal exposed a stale `model=None` argument to `run_backtest()`.
  - This would have broken the daily workflow accuracy step on this branch.
  - Regression updated in `tests/pipeline/test_sync_retained_prediction_corpus.py`.
- Updated mobile smoke expectations to match the current single-model nav: Home, Predictions, Performance, Replay.

## Live Supabase Rehearsal

- Ran active-band pipeline/live smoke through `npm run verify:python`.
- Forced retained-corpus refresh with `--no-incremental --require-results` for:
  - Goose: 50 rows, window 2025-06-20 to 2026-05-09
  - Phish: 50 rows, window 2025-04-27 to 2026-05-02
  - WSP: 50 rows, window 2025-03-23 to 2026-05-10
  - Billy Strings: 50 rows, window 2025-09-05 to 2026-04-18
  - UM: 50 rows, window 2026-02-11 to 2026-05-03
- Strict Supabase audits passed for all active bands:
  - predictions=1
  - projection_rows=50
  - historical_dates=50
  - accuracy_rows=50
- Supported-model freshness passed within 48h for predictions and accuracy across all active bands.

## Validation

```bash
npm run verify:python
npm run verify:docs
npm run verify:web
uv run pytest tests/data_collection/test_correction_detector.py tests/test_daily_workflow_contract.py tests/models/ tests/pipeline/test_run_backtest.py -v
uv run python scripts/check_version_sync.py
```

## GitHub Actions Signal

- Latest `main` scheduled daily pipeline failed on Goose for the same partial-setlist retained-corpus issue fixed here.
- Latest `dev` PR quality runs are from May 19 and predate today's commits; local gates and live rehearsal now provide the fresh signal, but PR CI should still be allowed to run before merge.

## Follow-Ups

- Band-list harmonization remains deferred.
- Consider whether forced retained-corpus refresh should be an explicit manual workflow option for all-scored windows where freshness reporting matters.

## Next Step

- Run the final manual local website review, then open the PR from `dev` to `main` and let fresh PR CI complete before merge.
