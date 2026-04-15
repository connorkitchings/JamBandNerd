-- Drop legacy football tables (pre-JamBandNerd pivot)
DROP TABLE IF EXISTS public.games CASCADE;
DROP TABLE IF EXISTS public.plays CASCADE;

-- Drop legacy generic Goose-only tables (superseded by goose_*_raw)
DROP TABLE IF EXISTS public.transitions CASCADE;
DROP TABLE IF EXISTS public.venues CASCADE;
DROP TABLE IF EXISTS public.songs CASCADE;
DROP TABLE IF EXISTS public.setlists CASCADE;
DROP TABLE IF EXISTS public.shows CASCADE;

-- Drop legacy Goose-only prediction table (superseded by predictions_notebook)
DROP TABLE IF EXISTS public.goose_notebook_predictions CASCADE;
