-- Rebuild Umphrey's McGee raw tables to align with official API v2
-- This migration drops the old tables and recreates them with API IDs as primary keys

-- Drop existing tables (dependent first)
drop table if exists public.um_setlists_raw;
drop table if exists public.um_shows_raw;
drop table if exists public.um_songs_raw;
drop table if exists public.um_venues_raw;

-- 1. UM Shows Raw
create table public.um_shows_raw (
    show_id bigint primary key,
    source_url text not null,
    show_date date not null,
    venue_name text,
    venue_city text,
    venue_state text,
    venue_country text,
    show_notes text,
    show_year integer,
    show_month integer,
    show_day integer,
    tour_name text,
    source_hash text not null,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create unique index if not exists um_shows_raw_source_url_idx on public.um_shows_raw (source_url);
create index if not exists um_shows_raw_show_date_idx on public.um_shows_raw (show_date);

-- 2. UM Setlists Raw
create table public.um_setlists_raw (
    id bigserial primary key,
    show_id bigint not null references public.um_shows_raw(show_id) on delete cascade,
    song_id bigint,
    song_name text,
    set_label text,
    set_sequence integer,
    song_position integer,
    show_position integer,
    transition text,
    is_segue boolean default false,
    encore boolean default false,
    footnote_text text,
    source_hash text not null,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists um_setlists_raw_show_id_idx on public.um_setlists_raw (show_id);
create unique index if not exists um_setlists_raw_show_position_idx on public.um_setlists_raw (show_id, show_position);

-- 3. UM Songs Raw
create table public.um_songs_raw (
    song_name text primary key,
    song_id bigint,
    original_artist text,
    debut_date date,
    last_played date,
    times_played_live integer default 0,
    avg_show_gap double precision,
    is_original boolean,
    source_hash text not null,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index if not exists um_songs_raw_song_id_idx on public.um_songs_raw (song_id);

-- 4. UM Venues Raw
create table public.um_venues_raw (
    venue_id bigint primary key,
    venue_name text not null,
    venue_city text,
    venue_state text,
    venue_country text,
    times_played integer default 0,
    last_played date,
    source_hash text not null,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create unique index if not exists um_venues_raw_unique_idx on public.um_venues_raw (venue_name, venue_city, venue_state, venue_country);
