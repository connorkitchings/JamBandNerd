create table if not exists public.eggy_songs_raw (
    id bigserial primary key,
    api_song_id text not null,
    song_name text not null,
    first_played date,
    last_played date,
    times_played integer not null default 0,
    average_length_seconds integer,
    source_hash text not null,
    api_created_at timestamptz,
    api_updated_at timestamptz,
    ingested_at timestamptz not null default timezone('utc'::text, now())
);

create unique index if not exists eggy_songs_raw_api_song_id_key
    on public.eggy_songs_raw(api_song_id);

create table if not exists public.eggy_shows_raw (
    id bigserial primary key,
    show_id text not null,
    show_date date,
    venue_name text,
    venue_city text,
    venue_state text,
    venue_country text,
    tour_name text,
    source_hash text not null,
    api_created_at timestamptz,
    api_updated_at timestamptz,
    ingested_at timestamptz not null default timezone('utc'::text, now())
);

create unique index if not exists eggy_shows_raw_show_id_key
    on public.eggy_shows_raw(show_id);

create index if not exists idx_eggy_shows_raw_show_date
    on public.eggy_shows_raw(show_date);

create table if not exists public.eggy_venues_raw (
    id bigserial primary key,
    venue_id text not null,
    venue_name text,
    city text,
    state text,
    country text,
    zip text,
    capacity integer,
    slug text,
    source_hash text not null,
    api_created_at timestamptz,
    ingested_at timestamptz not null default timezone('utc'::text, now())
);

create unique index if not exists eggy_venues_raw_venue_id_key
    on public.eggy_venues_raw(venue_id);

create table if not exists public.eggy_setlists_raw (
    id bigserial primary key,
    show_id text not null,
    set_number integer not null,
    song_position integer not null,
    song_name text not null,
    encore boolean not null default false,
    notes text,
    source_hash text not null,
    api_created_at timestamptz,
    api_updated_at timestamptz,
    ingested_at timestamptz not null default timezone('utc'::text, now())
);

create unique index if not exists eggy_setlists_raw_show_id_set_number_song_position_key
    on public.eggy_setlists_raw(show_id, set_number, song_position);

create index if not exists idx_eggy_setlists_raw_show_id
    on public.eggy_setlists_raw(show_id);
;
