-- Drop the unique constraint on song_name and add api_song_id
ALTER TABLE goose_songs_raw DROP CONSTRAINT IF EXISTS goose_songs_raw_song_name_key;
ALTER TABLE goose_songs_raw ADD COLUMN IF NOT EXISTS api_song_id INTEGER UNIQUE NOT NULL DEFAULT 0;

-- Create index on api_song_id for performance
CREATE INDEX IF NOT EXISTS idx_goose_songs_raw_api_song_id ON goose_songs_raw(api_song_id);;
