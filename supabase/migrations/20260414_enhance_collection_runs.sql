-- Enhance collection_runs with metadata for incremental collection decisions.

ALTER TABLE public.collection_runs
    ADD COLUMN IF NOT EXISTS status text DEFAULT 'success',
    ADD COLUMN IF NOT EXISTS rows_collected integer,
    ADD COLUMN IF NOT EXISTS duration_seconds double precision,
    ADD COLUMN IF NOT EXISTS max_show_date date;

-- Index for incremental queries: find the latest run's max_show_date per band.
CREATE INDEX IF NOT EXISTS ix_collection_runs_band_max_date
    ON public.collection_runs (band, max_show_date DESC);
