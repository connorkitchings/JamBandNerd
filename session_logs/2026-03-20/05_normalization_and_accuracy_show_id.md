# 2026-03-20 Session Log 05

## Goal

Implement the first code slice from the new data strategy:

- unify prediction-input normalization
- keep show sequencing deterministic
- align `accuracy_per_show.show_id` with the normalized string identifier

## Changes Made

### Shared normalization contract

**New file:** `src/jambandnerd/transformations/normalization.py`

- Added the shared normalization helper for prediction inputs
- Added canonical show sorting by `show_date`, then `show_id`
- Centralized source-column alias handling for:
  - `show_id`
  - `show_date`
  - `song_name`

**Modified:** `scripts/common.py`

- `prepare_band_data()` now delegates to the shared normalization helper
- Added optional `band` argument so band-specific ID aliases can be applied from
  one place

**Modified:** `src/jambandnerd/transformations/gaps.py`

- Removed duplicated alias logic from `generate_model_data()`
- Added a normalized-input guard
- Reused the shared show sorter for `show_index` derivation

### Prediction/backtest alignment

**Modified:** `scripts/generate_predictions.py`

- Passes `band` into the shared normalization boundary

**Modified:** `scripts/run_backtest.py`

- Passes `band` into the shared normalization boundary
- Reuses the shared show sorter for completed-show ordering
- Stops hashing non-numeric `show_id` values before writing `accuracy_per_show`
- Persists normalized string `show_id` values directly

### Schema alignment

**New file:** `supabase/migrations/20260322_accuracy_per_show_show_id_text.sql`

- Changes `accuracy_per_show.show_id` from bigint to text

**Modified:** `docs/reference/schemas/unified_tables.md`

- Updated the documented `accuracy_per_show.show_id` type to `text`

### Tests

**New files:**

- `tests/pipeline/test_normalization_contract.py`
- `tests/pipeline/test_run_backtest.py`

Coverage added for:

- band-specific show ID normalization
- same-date deterministic show ordering
- backtest persistence of string `show_id`

## Validation

- `uv run pytest -q tests/pipeline/test_normalization_contract.py tests/pipeline/test_run_backtest.py tests/pipeline/test_band_transform_readiness.py tests/pipeline/test_run_optimized_pipeline.py`
  passed

## Operational Follow-Up

- Apply `20260322_accuracy_per_show_show_id_text.sql` in Supabase
- Rebuild derived accuracy history after the migration using the corrected text
  `show_id` contract
