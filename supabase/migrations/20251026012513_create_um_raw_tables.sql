create table if not exists public.um_songs_raw (
    song_name text primary key,
    original_artist text,
    debut_date date,
    last_played date,
    times_played_live integer,
    avg_show_gap double precision,
    source_hash text not null
);

create table if not exists public.um_venues_raw (
    id integer primary key,
    venue_name text not null,
    venue_city text,
    venue_state text,
    venue_country text,
    times_played integer,
    last_played date,
    source_hash text not null
);

create table if not exists public.um_shows_raw (
    show_id bigserial primary key,
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
    source_hash text not null
);

create unique index if not exists um_shows_raw_source_url_idx on public.um_shows_raw (source_url);

create table if not exists public.um_setlists_raw (
    id bigserial primary key,
    show_id bigint not null references public.um_shows_raw(show_id) on delete cascade,
    source_url text not null,
    show_date date,
    venue_name text,
    venue_city text,
    venue_state text,
    venue_country text,
    set_label text,
    set_sequence integer,
    song_position integer,
    show_position integer,
    song_name text,
    is_segue boolean,
    encore boolean,
    footnote_symbol text,
    footnote_text text,
    song_notes text,
    source_hash text not null
);

create unique index if not exists um_venues_raw_unique_idx on public.um_venues_raw (venue_name, venue_city, venue_state, venue_country);
create unique index if not exists um_setlists_raw_show_position_idx on public.um_setlists_raw (show_id, show_position);
;
