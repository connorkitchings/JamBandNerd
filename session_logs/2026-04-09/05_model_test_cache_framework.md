# Model Test Cache Framework

## Goal

Create a reusable framework for caching historical per-show model-test runs so
future experimental model comparisons do not repeatedly recompute the same
`last_50`-style prediction boards.

## Summary

- Added a new local cache module at
  `src/jambandnerd/models/model_test_cache.py`.
- The cache now stores one JSON artifact per historical scored-show context,
  keyed by stable experiment metadata plus band/model/show identity.
- `scripts/compare_models.py` now:
  - uses a local per-show cache by default
  - supports `--cache-dir`
  - supports `--no-local-cache`
  - supports `--publish-historical-runs`
  - reports cache hit/miss/write counts in `cache_summary`
- `src/jambandnerd/models/comparison.py` now provides a shared scored-run
  record shape so comparison runs and historical lineage use the same per-show
  contract.
- `scripts/run_backtest.py` now reuses that shared scored-run record builder
  before publishing to `historical_prediction_runs`.
- Added `.gitignore` coverage for
  `docs/reports/model_baselines/cache/` so default development caching does not
  dirty the repo.

## Validation

- `uv run ruff check src/jambandnerd/models/model_test_cache.py src/jambandnerd/models/comparison.py scripts/compare_models.py scripts/run_backtest.py tests/models/test_model_test_cache.py tests/pipeline/test_compare_models.py tests/pipeline/test_run_backtest.py`
- `uv run pytest tests/models/test_model_test_cache.py tests/pipeline/test_compare_models.py tests/pipeline/test_run_backtest.py tests/pipeline/test_evaluate_deal_model.py`

Result:
- Focused Ruff check passed.
- Focused pytest suite passed (`15 passed`).

## Real Smoke Check

Ran:

```bash
uv run python scripts/compare_models.py --candidate-model deal --band goose --window 2 --fresh-training --output /tmp/deal_cache_smoke.json
```

Observed:

- First run created a local cache at
  `docs/reports/model_baselines/cache/deal__shared_core_v1__950a0b2b4453dcb7`
  with `record_count=6`, `misses=6`, `writes=6`.
- A second identical run hit the cache cleanly with `hits=6`, `misses=0`,
  `writes=0`.

## Next Step

Use the new cache-backed comparison path for future experimental model work,
then consider whether a later tranche should add richer cache inspection or a
more restrictive publish policy for experimental variants beyond the current
`--deal-overrides` guard.
