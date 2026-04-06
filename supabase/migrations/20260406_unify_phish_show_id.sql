-- Rename api_show_id to_show_id in Phish raw tables
--
-- Phish was the only band using `api_show_id` as the show primary key column.
-- All other bands use `show_id`. This migration aligns Phish with the shared
-- convention. After deploying the matching code changes, re-collect Phish data
-- via: uv run python scripts/run_phish_collection.py --full-backfill

-- Inspect actual constraint/index names before running:
-- SELECT indexname FROM pg_indexes WHERE tablename IN ('phish_shows_raw', 'phish_setlists_raw');
-- SELECT conname FROM pg_constraint WHERE conrelid = 'phish_shows_raw'::regclass;

ALTER TABLE phish_shows_raw RENAME COLUMN api_show_id TO show_id;
ALTER TABLE phish_setlists_raw RENAME COLUMN api_show_id TO show_id;

-- Update band registry
UPDATE bands SET id_column = 'show_id' WHERE slug = 'phish';
