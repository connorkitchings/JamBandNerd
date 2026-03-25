create table if not exists public.wsp_shows_upcoming (
    show_id text primary key,
    show_date date,
    venue_name text,
    venue_city text,
    venue_state text,
    venue_country text,
    source_url text,
    created_at timestamptz default timezone('utc', now())
);
;
