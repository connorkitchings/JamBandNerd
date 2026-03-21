create table if not exists public.bands (
    slug text not null,
    display_name text not null,
    shows_table text not null,
    id_column text not null,
    is_active boolean not null default true,
    created_at timestamp with time zone not null default now(),
    constraint bands_pkey primary key (slug)
);

create index if not exists bands_is_active_idx on public.bands (is_active) where is_active = true;

comment on table public.bands is 'Registry of bands supported by JamBandNerd. Single write point for band metadata used by both the pipeline and website.';
comment on column public.bands.slug is 'URL-safe band identifier, e.g. goose, phish, wsp.';
comment on column public.bands.display_name is 'Human-readable band name shown in the UI.';
comment on column public.bands.shows_table is 'The raw shows table for this band, e.g. goose_shows_raw.';
comment on column public.bands.id_column is 'The primary key column name for shows in this band, e.g. show_id or api_show_id.';
comment on column public.bands.is_active is 'Whether this band is active and shown in the website band selector.';

insert into public.bands (slug, display_name, shows_table, id_column, is_active) values
    ('eggy',   'Eggy',               'eggy_shows_raw',   'show_id',      true),
    ('billy',  'Billy Strings',      'billy_shows_raw',  'show_id',      true),
    ('goose',  'Goose',              'goose_shows_raw',  'show_id',      true),
    ('phish',  'Phish',              'phish_shows_raw',  'api_show_id', true),
    ('wsp',    'Widespread Panic',   'wsp_shows_raw',    'show_id',      true),
    ('um',     'Umphrey''s McGee',   'um_shows_raw',     'show_id',      true)
on conflict (slug) do update set
    display_name = excluded.display_name,
    shows_table  = excluded.shows_table,
    id_column    = excluded.id_column,
    is_active    = excluded.is_active;
