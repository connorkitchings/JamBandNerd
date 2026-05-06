# Session 01: Phish Promotion Rollout

## Goal
Run the operational rollout for the promoted Phish model
`phish_fast_gbm_v2_feat_notebook_rank_venue_run`, verify Supabase publication,
and record the resulting validation status.

## Constraints
- Current public site should remain Notebook/Deal only.
- Do not leave promoted single-band Phish rows in Supabase.
- Do not create new Supabase tables or run migrations.
- Preserve the existing Notebook/Deal website data surface.

## Result
- Forced Phish optimized pipeline was run:
  `uv run python scripts/run_optimized_pipeline.py --band phish --force`.
- This unintentionally published the Phish promoted-model rows to existing
  Supabase `setlist_*` tables.
- Cleanup removed the unintended model-specific Supabase footprint:
  - `setlist_prediction_songs`: 25 rows deleted.
  - `setlist_predictions`: 1 row deleted.
  - `setlist_accuracy`: 50 rows deleted.
  - `setlist_results`: 50 rows deleted.
- Follow-up count check confirmed zero rows remain in all four `setlist_*`
  tables for `phish_fast_gbm_v2_feat_notebook_rank_venue_run`.

## Fixes Made During Rollout
- `src/jambandnerd/models/deal/serialization.py`
  - Made the shared single-band serializer accept fast-predictor outputs that
    expose `gap_shows` instead of Deal's `current_gap`.
  - Preserves unavailable Deal-only diagnostics as `None`.
- `scripts/run_backtest.py`
  - Removed non-schema `target_show_date` from the `setlist_accuracy` payload;
    canonical table column is `show_date`.
- `scripts/run_optimized_pipeline.py`
  - Centralized the retained corpus window at 50 and passed that window to
    accuracy validation and Supabase audit.
- `.github/workflows/daily-pipeline.yml`
  - Passed `--replay-window 50` to accuracy validation and Supabase audit so CI
    validates the same retained corpus window it writes.
- Tests added or updated for serializer compatibility, accuracy payload shape,
  active-model test fixtures, and retained-window validation.

## Files Changed or Artifacts Produced
- `.github/workflows/daily-pipeline.yml`
- `scripts/run_backtest.py`
- `scripts/run_optimized_pipeline.py`
- `src/jambandnerd/models/deal/serialization.py`
- `tests/models/test_deal_serialization.py`
- `tests/pipeline/test_run_backtest.py`
- `tests/test_validate_accuracy_tables.py`
- `session_logs/2026-05-06/01_phish_promotion_rollout.md`
- Supabase cleanup artifact: all unintended
  `phish_fast_gbm_v2_feat_notebook_rank_venue_run` rows removed from
  `setlist_prediction_songs`, `setlist_predictions`, `setlist_accuracy`, and
  `setlist_results`.

## Commands Run
```bash
uv run python scripts/run_optimized_pipeline.py --band phish --force
uv run pytest tests/models/test_deal_serialization.py tests/pipeline/test_generate_live_predictions.py -q
uv run pytest tests/pipeline/test_run_backtest.py tests/models/test_deal_serialization.py tests/pipeline/test_generate_live_predictions.py -q
uv run pytest tests/pipeline/test_run_optimized_pipeline.py tests/test_daily_workflow_contract.py tests/test_validate_accuracy_tables.py tests/pipeline/test_run_backtest.py tests/models/test_deal_serialization.py tests/pipeline/test_generate_live_predictions.py -q
uv run pytest tests/models/ -q
uv run pytest tests/pipeline/test_generate_live_predictions.py tests/pipeline/test_run_optimized_pipeline.py -q
uv run pytest tests/test_daily_workflow_contract.py -q
uv run black --check src/jambandnerd/models/deal/serialization.py scripts/run_backtest.py scripts/run_optimized_pipeline.py tests/models/test_deal_serialization.py tests/pipeline/test_run_backtest.py tests/test_validate_accuracy_tables.py
uv run ruff check src/jambandnerd/models/deal/serialization.py scripts/run_backtest.py scripts/run_optimized_pipeline.py tests/models/test_deal_serialization.py tests/pipeline/test_run_backtest.py tests/test_validate_accuracy_tables.py
npm run verify:python
npm run verify:docs
npm run verify:web
uv run python -c "<count unintended phish setlist_* rows>"
uv run python -c "<delete unintended phish setlist_* rows>"
uv run python -c "<verify unintended phish setlist_* rows are zero>"
```

## Validation Status
- `uv run pytest tests/models/ -q` -> 179 passed.
- `uv run pytest tests/pipeline/test_generate_live_predictions.py tests/pipeline/test_run_optimized_pipeline.py -q` -> 28 passed.
- `uv run pytest tests/test_daily_workflow_contract.py -q` -> 3 passed.
- Affected combined suite -> 45 passed.
- Touched-file Black check -> passed.
- Touched-file Ruff check -> passed.
- `npm run verify:docs` -> passed.
- `npm run verify:web` -> passed, with 10 passed and 10 skipped smoke tests.
- `npm run verify:python` -> failed at branch-wide Black check because 15
  unrelated existing files would be reformatted. None were files touched in
  this rollout.

## Notes
- The first rollout attempt exposed a serializer mismatch for fast predictors.
- The second attempt wrote live predictions and then exposed the
  `setlist_accuracy` schema mismatch.
- The third attempt saved the retained 50-row corpus and exposed the 50-vs-100
  validation-window mismatch.
- The final pipeline attempt completed end to end, but that was not the desired
  production state because the current site should remain Notebook/Deal only.
- Existing Supabase tables were modified; no new Supabase tables were created.
- The unintended single-band model rows were deleted afterward.

## Next Step
Keep the production website on Notebook/Deal tables until the single-model
site cutover is explicitly requested, then run the cutover as a separate
planned release with a dry-run/read-only verification pass first.
