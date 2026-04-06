-- Add source_hash column to track changes from the source API
ALTER TABLE public.phish_songs_raw
ADD COLUMN IF NOT EXISTS source_hash TEXT;

ALTER TABLE public.phish_shows_raw
ADD COLUMN IF NOT EXISTS source_hash TEXT;

ALTER TABLE public.phish_venues_raw
ADD COLUMN IF NOT EXISTS source_hash TEXT;

ALTER TABLE public.phish_setlists_raw
ADD COLUMN IF NOT EXISTS source_hash TEXT;;
