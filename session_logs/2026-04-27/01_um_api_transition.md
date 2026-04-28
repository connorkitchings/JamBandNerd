# UM API Transition and Schema Rebuild

## Goal
Transition Umphrey's McGee (`um`) data collection to the official JSON API (v2) and rebuild the Supabase raw tables to use stable API identifiers as primary keys.

## Constraints
- Preserve rich statistical data for songs and venues that the JSON API currently lacks by maintaining targeted HTML scraping and merging with API IDs.
- Ensure all historical and future shows (up to 2026) are correctly ingested.
- Relax health checks for UM specifically as its API root returns a 500 but subpaths work correctly.

## Commands Run
- `uv run pytest tests/data_collection/test_um_collector.py`
- `uv run python scripts/run_um_collection.py --full-backfill`

## Files Changed
- `src/jambandnerd/data_collection/um/collector.py`: Transitioned to JSON API for shows/setlists; merged scraping for venues/songs.
- `src/jambandnerd/data_collection/um/normalizer.py`: Updated to handle API-driven columns and calculate manual set positions.
- `src/jambandnerd/data_collection/config.py`: Updated UM `base_url` to the API endpoint.
- `scripts/run_um_collection.py`: Simplified orchestration to use API IDs for conflict resolution.
- `scripts/common.py`: Relaxed health check for UM to handle unstable API root.
- `supabase/migrations/20260427_rebuild_um_raw_tables.sql`: New schema with API-aligned primary keys.
- `tests/data_collection/test_um_collector.py`: Updated to match API-driven logic.
- `docs/reference/schemas/um_allthings.md`: Updated to document the new API-driven schema.

## Validation Status
- ✅ Unit tests passing.
- ✅ Full backfill successful: 2,938 shows and 48,072 setlist rows ingested into the new schema.
- ✅ Future shows (up to August 2026) correctly ingested.

## Next Step
Monitor the daily pipeline to ensure the new UM collector integrates correctly with the overall orchestration.
