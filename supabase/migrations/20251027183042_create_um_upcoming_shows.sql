create table if not exists public.um_upcoming_shows (
    source_uuid uuid primary key,
    starts_at timestamptz,
    starts_at_local date,
    ends_at timestamptz,
    venue_name text,
    formatted_address text,
    city text,
    region text,
    country text,
    details text,
    exchange_listing_url text,
    vip_link_url text,
    is_sold_out boolean,
    is_collecting_waitlist boolean,
    source_hash text not null,
    created_at timestamptz default timezone('utc', now()),
    updated_at timestamptz default timezone('utc', now())
);

create index if not exists um_upcoming_shows_starts_at_idx on public.um_upcoming_shows (starts_at);
;
