-- Add query performance indexes to band raw tables.
-- Apply this in Supabase SQL Editor or through the Supabase CLI.

-- Indexes for show_date queries (temporal lookups, recent shows, date ranges)
CREATE INDEX IF NOT EXISTS goose_shows_raw_show_date_idx ON goose_shows_raw (show_date);
CREATE INDEX IF NOT EXISTS eggy_shows_raw_show_date_idx ON eggy_shows_raw (show_date);
CREATE INDEX IF NOT EXISTS phish_shows_raw_show_date_idx ON phish_shows_raw (show_date);
CREATE INDEX IF NOT EXISTS wsp_shows_raw_show_date_idx ON wsp_shows_raw (show_date);
CREATE INDEX IF NOT EXISTS billy_shows_raw_show_date_idx ON billy_shows_raw (show_date);
CREATE INDEX IF NOT EXISTS um_shows_raw_show_date_idx ON um_shows_raw (show_date);

-- Indexes for show_id lookups (setlist joins, relationship queries)
CREATE INDEX IF NOT EXISTS goose_setlists_raw_show_id_idx ON goose_setlists_raw (show_id);
CREATE INDEX IF NOT EXISTS eggy_setlists_raw_show_id_idx ON eggy_setlists_raw (show_id);
CREATE INDEX IF NOT EXISTS phish_setlists_raw_show_id_idx ON phish_setlists_raw (show_id);
CREATE INDEX IF NOT EXISTS wsp_setlists_raw_show_id_idx ON wsp_setlists_raw (show_id);
CREATE INDEX IF NOT EXISTS billy_setlists_raw_show_id_idx ON billy_setlists_raw (show_id);
CREATE INDEX IF NOT EXISTS um_setlists_raw_show_id_idx ON um_setlists_raw (show_id);

-- Composite indexes for common access patterns (date + artist filtering)
CREATE INDEX IF NOT EXISTS phish_shows_raw_date_artist_idx ON phish_shows_raw (show_date, artist_name);

-- Partial indexes for recent data (last 2 years) - useful for prediction lookups
-- Note: PostgreSQL doesn't support partial indexes on inherited tables directly,
-- so these would need to be created per-table if needed:
-- CREATE INDEX IF NOT EXISTS goose_shows_raw_recent_idx ON goose_shows_raw (show_date)
--   WHERE show_date > CURRENT_DATE - INTERVAL '2 years';

COMMENT ON INDEX goose_shows_raw_show_date_idx IS 'Improves temporal queries for Goose shows';
COMMENT ON INDEX goose_setlists_raw_show_id_idx IS 'Improves setlist-to-show joins';
