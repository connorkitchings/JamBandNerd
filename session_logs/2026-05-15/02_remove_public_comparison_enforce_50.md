# Remove Public Comparison UX And Enforce 50-Show Retention

## Summary
- Implemented exact retained-window enforcement for active single-model `setlist_*` accuracy/result rows.
- Kept public website navigation focused on Home, Predictions, and Performance, with mobile ordering Home, Stats, Predict.
- Preserved offline model-comparison tooling for future promotion evidence.

## Changes
- `scripts/run_backtest.py` now prunes the retained corpus even when incremental scoring finds every selected show already scored.
- `scripts/validate_accuracy_tables.py` gained `--require-exact-retained-window`, which checks active `BandMetadata.model_version` rows in both `setlist_accuracy` and `setlist_results`.
- Daily workflow and local optimized pipeline accuracy validation now require exact 50-row retention.
- Web smoke/unit tests now assert the public nav has no Compare item and keeps the expected mobile order.

## Supabase Alignment
- Before sync, Goose, Phish, and Billy each retained 100 active-version rows in `setlist_accuracy` and `setlist_results`.
- Ran retained-corpus sync with `--window 50 --incremental` for Goose, Phish, WSP, Billy, and UM.
- Goose, Phish, and Billy each pruned 50 older completed-show rows; WSP and UM were already at 50.
- Final validation passed: all active bands retain exactly 50 active-version rows in both `setlist_accuracy` and `setlist_results`.

## Verification
- `uv run pytest -q tests/pipeline/test_run_backtest.py tests/test_validate_accuracy_tables.py`
- `uv run ruff check scripts/run_backtest.py scripts/validate_accuracy_tables.py scripts/run_optimized_pipeline.py tests/pipeline/test_run_backtest.py tests/test_validate_accuracy_tables.py`
- `npm run test:unit --workspace apps/web`
- `uv run python scripts/validate_accuracy_tables.py --max-age-hours 72 --replay-window 50 --skip-freshness --require-exact-retained-window`
- `npm run verify:web`
- `npm run verify:docs`
- `npm run verify:python`
