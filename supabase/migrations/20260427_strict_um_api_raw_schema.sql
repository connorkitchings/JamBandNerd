-- Align Umphrey's McGee song and venue raw tables with strict API-only ingestion.
-- Historical scrape-only song/venue stats are intentionally removed; rerun
-- scripts/run_um_collection.py --full-backfill after applying this migration.

truncate table public.um_songs_raw;

alter table public.um_songs_raw
    add column if not exists song_id bigint,
    add column if not exists song_slug text,
    add column if not exists api_created_at timestamptz,
    add column if not exists api_updated_at timestamptz;

alter table public.um_songs_raw drop constraint if exists um_songs_raw_pkey;
alter table public.um_songs_raw alter column song_id set not null;
alter table public.um_songs_raw add constraint um_songs_raw_pkey primary key (song_id);

drop index if exists public.um_songs_raw_song_id_idx;
drop index if exists public.um_songs_raw_song_name_idx;

alter table public.um_songs_raw
    drop column if exists debut_date,
    drop column if exists last_played,
    drop column if exists times_played_live,
    drop column if exists avg_show_gap;

alter table public.um_venues_raw
    add column if not exists venue_slug text,
    add column if not exists venue_zip text,
    add column if not exists capacity integer,
    drop column if exists times_played,
    drop column if exists last_played;

drop index if exists public.um_venues_raw_unique_idx;
