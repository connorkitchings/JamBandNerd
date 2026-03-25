DROP TABLE IF EXISTS public.wsp_songs_raw;

CREATE TABLE public.wsp_songs_raw (
    song_id SERIAL PRIMARY KEY,
    song_code TEXT,
    song_name TEXT NOT NULL UNIQUE,
    aka TEXT,
    first_played DATE,
    last_played DATE,
    times_played INTEGER,
    is_cover BOOLEAN DEFAULT false,
    original_artist TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_hash TEXT
);;
