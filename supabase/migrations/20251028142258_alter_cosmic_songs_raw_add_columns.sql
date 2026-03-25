alter table public.cosmic_songs_raw
    add column if not exists written_by text,
    add column if not exists lyrics text,
    add column if not exists shortest_version_played_at date,
    add column if not exists longest_version_played_at date;
;
