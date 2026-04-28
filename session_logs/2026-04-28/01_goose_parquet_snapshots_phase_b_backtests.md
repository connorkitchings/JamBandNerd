# Goose Parquet Snapshots + Phase B Backtests

## Goal

Refresh Goose local raw-table data, verify the snapshot backtest path, and run
Phase B Goose model comparisons without Supabase prediction/history writes.

## Constraints

- Stay on `feat/single-model-per-band`.
- Use local snapshots for model iteration.
- Preserve the `reference_date` anti-leakage boundary.
- Keep generated model evidence under ignored local artifacts.

## Commands Run

```bash
uv run python scripts/export_backtest_snapshots.py --band goose --snapshot-root .snapshots/goose_phase_b
uv run python scripts/run_backtest.py --band goose --shows 3 --snapshot-root .snapshots/goose_phase_b --dry-run --no-incremental --require-results
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GoosePredictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv lock
uv run pytest tests/test_table_snapshots.py -q
uv run python scripts/export_backtest_snapshots.py --band goose --snapshot-root .snapshots/goose_phase_b --format parquet
uv run python scripts/run_backtest.py --band goose --shows 3 --snapshot-root .snapshots/goose_phase_b --dry-run --no-incremental --require-results
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseLogisticV2Predictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv run python scripts/run_phase_b_backtest.py --band goose --predictor jambandnerd.models.goose.model.GooseGbmV2Predictor --shows 50 --snapshot-root .snapshots/goose_phase_b --out-dir .snapshots/goose_phase_b/backtests
uv run python scripts/promote_phase_b_winner.py --incumbent .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v1_summary.json --candidate .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v2_logistic_summary.json --min-shows 50
uv run python scripts/promote_phase_b_winner.py --incumbent .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v1_summary.json --candidate .snapshots/goose_phase_b/backtests/goose_goose_phase_b_v2_gbm_summary.json --min-shows 50
uv run ruff check scripts/run_phase_b_backtest.py scripts/promote_phase_b_winner.py scripts/export_backtest_snapshots.py scripts/common.py src/jambandnerd/db/table_snapshots.py tests/test_table_snapshots.py
uv run black --check scripts/run_phase_b_backtest.py scripts/promote_phase_b_winner.py scripts/export_backtest_snapshots.py scripts/common.py src/jambandnerd/db/table_snapshots.py tests/test_table_snapshots.py
npm run verify:docs
```

## Files Changed / Artifacts Produced

- Added `pyarrow` runtime dependency and lockfile entry.
- Added JSON/Parquet snapshot format support in `table_snapshots.py`,
  `scripts/common.py`, and `scripts/export_backtest_snapshots.py`.
- Fixed Phase B helper imports so dotted predictor paths pass the
  `PredictionModel` subclass check.
- Updated snapshot tests and docs for Parquet snapshots.
- Local ignored artifacts:
  - `.snapshots/goose_phase_b/goose_shows_raw.parquet`
  - `.snapshots/goose_phase_b/goose_setlists_raw.parquet`
  - `.snapshots/goose_phase_b/backtests/*`

## Results

Snapshot row counts:

- `goose_shows_raw`: 834
- `goose_setlists_raw`: 7136

Parquet size comparison:

- `goose_shows_raw`: 376K JSON -> 112K Parquet
- `goose_setlists_raw`: 2.7M JSON -> 588K Parquet

50-show model comparison:

| Model | p@10 | p@25 | r@50 | dual | Gate |
|---|---:|---:|---:|---:|---|
| `goose_phase_b_v1` | 0.246 | 0.198 | 0.526 | 0.386 | incumbent |
| `goose_phase_b_v2_logistic` | 0.242 | 0.197 | 0.528 | 0.385 | not eligible |
| `goose_phase_b_v2_gbm` | 0.250 | 0.194 | 0.533 | 0.392 | not eligible |

## Validation Status

- `uv run pytest tests/test_table_snapshots.py -q` -> passed, 5 tests.
- Targeted `uv run ruff check ...` -> passed.
- Targeted `uv run black --check ...` -> passed.
- `npm run verify:docs` -> passed.
- Full `npm run verify:python`, web, and clean were not run.

## Next Step

Do not promote the current Goose v2 candidates. Either tune the GBM/logistic
feature set against the 50-show evidence or run a 100-show gate only after a
candidate shows a stronger 50-show signal.
