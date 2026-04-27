# UM Strict API Collector Cleanup

## Goal
Convert Umphrey's McGee collection to strict All Things Umphrey's JSON API usage and align Supabase schema, diagnostics, docs, and tests with the API-backed raw tables.

## Constraints
- Keep UM-specific source behavior inside `src/jambandnerd/data_collection/um/` and `scripts/run_um_collection.py`.
- Do not reintroduce legacy `set_number` for UM setlists; keep `set_sequence`, `song_position`, and `show_position`.
- Keep daily workflow orchestration unchanged unless tests show drift.

## Commands Run
- `uv run python -m compileall -q src/jambandnerd/data_collection/um scripts/run_um_collection.py scripts/diagnose_band_data.py`
- `uv run black src/jambandnerd/data_collection/um/collector.py src/jambandnerd/data_collection/um/normalizer.py scripts/run_um_collection.py scripts/diagnose_band_data.py tests/data_collection/test_um_collector.py tests/data_collection/test_um_normalization.py tests/pipeline/test_run_um_collection.py tests/test_data_diagnostics_scripts.py`
- `uv run ruff check src/jambandnerd/data_collection/um/collector.py src/jambandnerd/data_collection/um/normalizer.py scripts/run_um_collection.py scripts/diagnose_band_data.py tests/data_collection/test_um_collector.py tests/data_collection/test_um_normalization.py tests/pipeline/test_run_um_collection.py tests/test_data_diagnostics_scripts.py`
- `uv run pytest tests/data_collection/test_um_collector.py tests/data_collection/test_um_normalization.py tests/pipeline/test_run_um_collection.py tests/test_data_diagnostics_scripts.py`
- `uv run pytest tests/test_daily_workflow_contract.py tests/pipeline/test_run_optimized_pipeline.py tests/test_collection_preflight.py`
- `npm run verify:docs`
- `uv run python scripts/run_um_collection.py --full-backfill`
- `uv run python scripts/diagnose_band_data.py --band um`

## Files Changed
- `src/jambandnerd/data_collection/um/collector.py`: removed remaining UM HTML scraping and mapped songs/venues from API JSON.
- `scripts/run_um_collection.py`: upserts songs on `song_id`, refreshes `um_upcoming_shows` on early exits, and removes web-scraping wording.
- `src/jambandnerd/data_collection/um/normalizer.py`: made optional setlist fields robust without adding legacy `set_number`.
- `scripts/diagnose_band_data.py`: uses UM-specific API setlist columns for diagnostics.
- `supabase/migrations/20260427_strict_um_api_raw_schema.sql`: aligns UM songs/venues raw schema with strict API fields.
- `docs/reference/schemas/um_allthings.md` and `docs/reference/specifications/data_strategy.md`: updated schema and setlist contract docs.
- Targeted UM and diagnostics tests updated.
- `.agent/PLAYBOOK.md`: captured the strict API-only schema cleanup pattern.

## Validation Status
- Targeted UM collector/orchestrator/diagnostics tests pass.
- Daily workflow contract, optimized pipeline, and collection preflight tests pass.
- Docs build passes with existing mkdocs nav warnings only.
- Live Supabase backfill ran successfully after dropping legacy uniqueness indexes on `um_songs_raw.song_name` and `um_venues_raw(venue_name, venue_city, venue_state, venue_country)`.
- Backfill counts: 1,119 songs, 1,073 venues, 2,927 shows, 47,815 setlist rows, 37 upcoming shows.
- `scripts/diagnose_band_data.py --band um` passed with no issues.

## Next Step
Run the daily workflow for UM and confirm predictions/accuracy publish cleanly from the refreshed raw tables.
