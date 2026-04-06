create table if not exists public.phish_venues_raw (
    api_venue_id bigint primary key,
    venue_name text,
    venue_city text,
    venue_state text,
    venue_country text,
    created_at timestamptz not null default now()
);

create index if not exists idx_phish_venues_raw_city_state on public.phish_venues_raw(venue_city, venue_state);;
