CREATE TABLE IF NOT EXISTS public.wsp_setlists_raw (
    id SERIAL PRIMARY KEY,
    show_id INTEGER NOT NULL REFERENCES public.wsp_shows_raw(show_id),
    set_number TEXT NOT NULL,
    song_position INTEGER NOT NULL,
    song_name TEXT NOT NULL,
    is_segue BOOLEAN DEFAULT false,
    song_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_hash TEXT,
    UNIQUE(show_id, set_number, song_position)
);;
