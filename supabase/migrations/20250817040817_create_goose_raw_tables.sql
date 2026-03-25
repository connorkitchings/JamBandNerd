-- Goose raw tables
CREATE TABLE IF NOT EXISTS goose_shows_raw (
  id SERIAL PRIMARY KEY,
  show_id VARCHAR(50) UNIQUE NOT NULL,
  show_date DATE NOT NULL,
  venue_name VARCHAR(255),
  venue_city VARCHAR(100),
  venue_state VARCHAR(50),
  venue_country VARCHAR(50),
  tour_name VARCHAR(100),
  source_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goose_setlists_raw (
  id SERIAL PRIMARY KEY,
  show_id VARCHAR(50) NOT NULL,
  set_number INTEGER NOT NULL,
  song_position INTEGER NOT NULL,
  song_name VARCHAR(255) NOT NULL,
  song_length_seconds INTEGER,
  encore BOOLEAN DEFAULT FALSE,
  notes TEXT,
  source_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (show_id, set_number, song_position)
);

CREATE INDEX IF NOT EXISTS idx_goose_setlists_raw_show_id ON goose_setlists_raw (show_id);

CREATE TABLE IF NOT EXISTS goose_songs_raw (
  id SERIAL PRIMARY KEY,
  song_name VARCHAR(255) UNIQUE NOT NULL,
  first_played DATE,
  last_played DATE,
  times_played INTEGER DEFAULT 0,
  average_length_seconds INTEGER,
  source_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
;
