# 2026-04-10 — Deal accuracy schema fix and historical backfill kickoff

## Summary

- Added a Supabase migration to convert `accuracy_deal` to the unified wide
  aggregate-accuracy schema expected by `scripts/save_aggregate_accuracy.py`.
- Updated Deal schema/reference docs to reflect the promoted Deal rollout state
  and the current aggregate table contract.
- Applied the new `accuracy_deal` schema migration and the Deal public-read
  grant migration to the linked Supabase project using an isolated temporary
  Supabase workdir, to avoid replaying legacy local migrations with duplicate
  date-only prefixes.
- Verified live aggregate publishing for Billy Deal over the most recent 50
  scored shows.
- Started Goose Deal full-history backfill, confirmed historical scored runs are
  being written correctly, then stopped the run at a controlled checkpoint after
  confirming throughput was too slow to finish Goose, Eggy, and Billy in a
  single session.

## Files Changed

- `supabase/migrations/20260410221500_unify_accuracy_deal_schema.sql`
- `docs/reference/models/deal.md`
- `docs/reference/schemas/deal_tables.md`
- `docs/reference/schemas/unified_tables.md`
- `docs/reference/specifications/predictions_schema.md`

## Verification

- `uv run pytest tests/models/test_model_registry.py tests/pipeline/test_save_aggregate_accuracy.py tests/test_validate_accuracy_tables.py -q`
  - `14 passed`
- `uv run python scripts/save_aggregate_accuracy.py --band billy --model deal --shows 50`
  - succeeded and wrote a live `accuracy_deal` row
- `uv run python -c "from src.jambandnerd.db.operations import get_table_schema; ..."`
  - confirmed live `accuracy_deal` columns now include:
    - `num_shows`
    - `evaluated_at`
    - `k10_*`, `k25_*`, `k50_*`

## Live Data State

### Billy aggregate accuracy

- `accuracy_deal` now has a live Billy row for:
  - `window_start=2025-08-16`
  - `window_end=2026-04-08`
  - `num_shows=50`
- Billy Deal aggregate metrics saved:
  - `K=10 hit_rate=0.780 precision=0.248 recall=0.110`
  - `K=25 hit_rate=0.900 precision=0.205 recall=0.216`
  - `K=50 hit_rate=0.900 precision=0.152 recall=0.315`

### Goose historical backfill checkpoint

- Started:
  - `uv run python scripts/run_backtest.py --band goose --model deal --all-history`
- Confirmed live progress before stopping:
  - `historical_prediction_runs` for Goose Deal increased from `0` to `111`
  - latest retained Goose Deal replay row reached `target_show_date=2019-04-04`
- `accuracy_per_show` for Goose Deal remained `0` at stop time because
  `run_backtest.py` batches the per-show upsert at the end of the run.
- The partial Goose run is resumable because `historical_prediction_runs`
  upserts on run context and can be rerun safely.

## Operational Notes

- The Supabase CLI was initially blocked by a malformed `SUPABASE_ACCESS_TOKEN`
  env override. Running with `env -u SUPABASE_ACCESS_TOKEN ...` allowed the CLI
  to fall back to the stored profile state.
- The main repo `supabase/migrations` directory currently contains older files
  with duplicate date-only prefixes (`20260321`, `20260323`), which makes a
  normal `supabase db push --include-all` unsafe against the linked project.
- The isolated temporary workdir workaround is currently the safest way to push
  only the intended Deal migrations:
  - `20260410221500_unify_accuracy_deal_schema.sql`
  - `20260410_grant_deal_tables_public_read.sql`

## Next Commands

Resume the ordered Deal full-history build:

1. Goose
   - `uv run python scripts/run_backtest.py --band goose --model deal --all-history`
   - `uv run python scripts/save_aggregate_accuracy.py --band goose --model deal --shows 50`
2. Eggy
   - `uv run python scripts/run_backtest.py --band eggy --model deal --all-history`
   - `uv run python scripts/save_aggregate_accuracy.py --band eggy --model deal --shows 50`
3. Billy
   - Billy aggregate is already saved for the current 50-show window
   - still needs full-history replay completion via:
     - `uv run python scripts/run_backtest.py --band billy --model deal --all-history`
     - `uv run python scripts/save_aggregate_accuracy.py --band billy --model deal --shows 50`

After each band, verify:

- `historical_prediction_runs` count for `(band, model_slug='deal')`
- `accuracy_per_show` count for `(band, model_version='deal_v2')`
- newest `accuracy_deal` row for the band
