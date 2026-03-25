create table if not exists public.goose_venues_raw (
  venue_id text primary key,
  venue_name text,
  city text,
  state text,
  country text,
  zip text,
  capacity integer,
  slug text,
  source_hash text,
  created_at timestamptz default now()
);;
