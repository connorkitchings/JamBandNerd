-- Align accuracy_per_show.show_id with the normalized string identifier
-- used throughout the ingestion and transformation pipeline.
-- Apply this in Supabase SQL Editor or through the Supabase CLI.

alter table public.accuracy_per_show
  alter column show_id type text
  using show_id::text;
