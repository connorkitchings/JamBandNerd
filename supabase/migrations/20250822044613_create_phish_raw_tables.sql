-- Create Phish raw tables (idempotent)
create table if not exists public.phish_songs_raw (
    api_song_id bigint primary key,
    song_name text,
    slug text,
    abbreviation text,
    artist text,
    debut_date date,
    last_played_date date,
    times_played integer,
    gap integer,
    last_permalink text,
    debut_permalink text,
    created_at timestamptz not null default now()
);

create table if not exists public.phish_shows_raw (
    api_show_id bigint primary key,
    show_year text,
    show_month bigint,
    show_day bigint,
    show_date date,
    permalink text,
    exclude_from_stats boolean,
    api_venue_id bigint,
    setlist_notes text,
    venue_name text,
    venue_city text,
    venue_state text,
    venue_country text,
    api_artist_id bigint,
    artist_name text,
    api_tour_id bigint,
    tour_name text,
    api_created_at timestamptz,
    api_updated_at timestamptz,
    created_at timestamptz not null default now()
);

create table if not exists public.phish_setlists_raw (
    api_unique_id bigint primary key,
    api_show_id bigint,
    show_date date,
    permalink text,
    api_song_id bigint,
    song_name text,
    set_number text,
    position integer,
    transition text,
    is_reprise boolean,
    is_jam boolean,
    is_jam_chart boolean,
    track_time text,
    gap integer,
    is_original boolean,
    footnote text,
    created_at timestamptz not null default now()
);

-- Helpful indexes
create index if not exists idx_phish_shows_raw_show_date on public.phish_shows_raw(show_date);
create index if not exists idx_phish_setlists_raw_show on public.phish_setlists_raw(api_show_id);
create index if not exists idx_phish_setlists_raw_song on public.phish_setlists_raw(api_song_id);
;
