create table if not exists public.cosmic_shows_raw (
    show_id bigint primary key,
    show_date date not null,
    venue_id bigint,
    venue_name text,
    city text,
    state text,
    country text,
    show_type text,
    source_url text,
    source_hash text not null,
    created_at timestamptz not null default timezone('utc'::text, now()),
    updated_at timestamptz not null default timezone('utc'::text, now())
);

create index if not exists idx_cosmic_shows_raw_show_date
    on public.cosmic_shows_raw(show_date);

create index if not exists idx_cosmic_shows_raw_venue_id
    on public.cosmic_shows_raw(venue_id);

create table if not exists public.cosmic_setlists_raw (
    id bigserial primary key,
    show_id bigint not null,
    song_id bigint,
    song_name text not null,
    set_number integer not null,
    song_position integer not null,
    is_segue boolean not null default false,
    encore boolean not null default false,
    song_notes text,
    source_hash text not null,
    created_at timestamptz not null default timezone('utc'::text, now())
);

create unique index if not exists cosmic_setlists_raw_show_id_set_number_song_position_key
    on public.cosmic_setlists_raw(show_id, set_number, song_position);

create index if not exists idx_cosmic_setlists_raw_show_id
    on public.cosmic_setlists_raw(show_id);

create table if not exists public.cosmic_songs_raw (
    song_id bigint primary key,
    song_name text not null,
    song_origin text,
    song_notes text,
    times_played integer,
    shortest_version_seconds integer,
    shortest_version_show_id bigint,
    longest_version_seconds integer,
    longest_version_show_id bigint,
    longest_gap_shows integer,
    longest_gap_start_show_id bigint,
    longest_gap_end_show_id bigint,
    longest_streak integer,
    longest_streak_start_show_id bigint,
    longest_streak_end_show_id bigint,
    source_hash text not null,
    created_at timestamptz not null default timezone('utc'::text, now()),
    updated_at timestamptz not null default timezone('utc'::text, now())
);

create table if not exists public.cosmic_venues_raw (
    venue_id bigint primary key,
    venue_name text not null,
    city text,
    state text,
    country text,
    source_url text,
    source_hash text not null,
    created_at timestamptz not null default timezone('utc'::text, now()),
    updated_at timestamptz not null default timezone('utc'::text, now())
);
;
