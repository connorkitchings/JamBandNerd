CREATE TABLE IF NOT EXISTS public.wsp_shows_raw (
    show_id SERIAL PRIMARY KEY,
    show_date DATE NOT NULL,
    venue_name TEXT,
    city TEXT,
    state TEXT,
    show_notes TEXT,
    source_url TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_hash TEXT
);;
