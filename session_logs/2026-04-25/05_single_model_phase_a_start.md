# Session 05 — Single-Model Phase A: Commits A1 + A2

**Branch**: `feat/single-model-per-band`
**Date**: 2026-04-25

## Goal

Begin Phase A code work: write the SQL migration for the four new `setlist_*` tables
(A1) and reshape the model registry to the band-keyed architecture (A2).

## Constraints

- Additive only in A2 — old slug-keyed registry API must remain intact until A4
  updates the pipeline scripts
- Eggy intentionally absent from all new band-keyed structures
- `verify:python` (352 tests) must pass before ending session

## Commands Run

```bash
npm run verify:python    # 352 passed, 6 skipped — clean
```

## Files Changed / Artifacts Produced

### Commit A1 — `b7913bc`
- `supabase/migrations/20260425_create_setlist_tables.sql` (new)
  - Four tables: `setlist_predictions`, `setlist_prediction_songs`,
    `setlist_results`, `setlist_accuracy`
  - `model_slug` dropped; unique key `(band, model_version, target_show_key)`
  - `weighted_precision_score` column (`0.2·p10 + 0.7·p25 + 0.1·p50`)
  - RLS enabled: `anon` SELECT, `service_role` FOR ALL
  - Schema-only; no rows written, no existing tables touched

### Commit A2 — `aa6b5cc` (+ lint fix `c780764`)
- `src/jambandnerd/models/baseline/__init__.py` (new)
- `src/jambandnerd/models/baseline/predictor.py` (new)
  - `BaselinePredictor(DealPredictor)`: per-band model artifacts at
    `models/baseline/{band}_baseline_v1.json`
- `src/jambandnerd/models/metadata.py`
  - Added `BandMetadata` dataclass and `BAND_METADATA` (5 bands)
  - Old `ModelMetadata` / `MODEL_METADATA` untouched
- `src/jambandnerd/models/registry.py`
  - Added `list_active_bands()`, `get_band_metadata()`, `get_band_model_version()`,
    `build_band_predictor()`, `get_band_serializer()`
  - Old slug-keyed functions untouched
- `src/jambandnerd/config/models.py`
  - Added `ACTIVE_BANDS`, `BAND_TOP_N`, `WEIGHTED_PRECISION_WEIGHTS`

## Validation Status

`npm run verify:python` — 352 passed, 6 skipped. Clean.

`verify:web` and `verify:docs` not run; no web or doc files changed this session.

## Next Step

**A3** — new `upsert_setlist_*` storage helpers in `src/jambandnerd/db/operations.py`;
old helpers untouched.
