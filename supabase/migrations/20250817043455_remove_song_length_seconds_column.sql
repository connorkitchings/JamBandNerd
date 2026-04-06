-- Remove song_length_seconds column from goose_setlists_raw
ALTER TABLE goose_setlists_raw DROP COLUMN IF EXISTS song_length_seconds;;
