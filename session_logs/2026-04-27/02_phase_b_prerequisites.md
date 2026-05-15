# Phase B Prerequisites and Supabase Migration

## Goal

Resolve all ADR 0001 open items before Phase B band-specific model work begins,
and apply the `setlist_*` schema to the live Supabase project.

## Constraints

- All work stays on `feat/single-model-per-band`. No merge to `main` until all
  5 active bands have specialized Phase B models (decided this session).
- Supabase table population will be run locally (not via GitHub Actions).
- Eggy remains excluded from Phase A; its onboard/exclude decision is deferred.

## Key Decision

**Merge gate (confirmed 2026-04-27):** `feat/single-model-per-band` does not
merge to `main` until Goose, Phish, WSP, Billy, and UM each have a promoted
Phase B model. Phase B order: Goose first.

## Commands Run

```bash
uv run pytest tests/models/test_accuracy_metrics.py tests/models/test_model_readiness.py -q
uv run pytest tests/ -q --tb=short
uv run ruff check <changed files>
uv run black --check <changed files>
```

## Files Changed

- `src/jambandnerd/models/accuracy.py` — added `compute_weighted_precision_score(p10, p25, p50)` using `WEIGHTED_PRECISION_WEIGHTS` from config; added import.
- `src/jambandnerd/models/readiness.py` — added `is_band_promotion_eligible(p25_new, p25_baseline, n_shows) -> bool` using `PHASE_B_MIN_BACKTEST_SHOWS` and `PHASE_B_MIN_PRECISION_AT_25_DELTA`.
- `src/jambandnerd/config/models.py` — removed dead `BAND_TOP_N` dict; source of truth is `BandMetadata.default_top_k`.
- `scripts/run_backtest.py` — replaced inline weighted-precision formula with call to `compute_weighted_precision_score()`; removed now-unused `WEIGHTED_PRECISION_WEIGHTS` import.
- `tests/models/test_accuracy_metrics.py` — new; 5 tests for `compute_weighted_precision_score`.
- `tests/models/test_model_readiness.py` — added 5 tests for `is_band_promotion_eligible`.

## Supabase

- Migration `supabase/migrations/20260425_create_setlist_tables.sql` applied to
  live project via Supabase SQL Editor.
- All 4 tables confirmed present with correct column counts and RLS policies
  (2 policies per table: anon SELECT, service_role ALL).
- Tables are currently empty; population via local pipeline run is next.

## Validation

- 352 passed, 6 skipped (full suite — unchanged from prior session).
- 25 passed for the directly changed tests.
- ruff + black: clean on all changed files.
- Not run: `npm run verify:web` (Playwright smokes require hosted target).

## Next Step

Populate `setlist_*` tables by running the local pipeline with Supabase
service-role credentials:
```bash
export SUPABASE_URL=...
export SUPABASE_SERVICE_ROLE_KEY=...
uv run python scripts/run_backtest.py --band all
uv run python scripts/generate_live_predictions.py --band all
```
Then verify row counts per band and run a Vercel preview smoke before starting
Phase B Goose work.
