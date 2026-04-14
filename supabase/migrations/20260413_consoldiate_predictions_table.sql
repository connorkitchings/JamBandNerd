-- Consolidate three model-specific prediction tables into a single unified table.
--
-- All three tables (predictions_notebook, predictions_deal, predictions_ckplus)
-- share an identical DDL schema.  We create a new unified `predictions` table
-- with the same columns plus a `model_slug` discriminator, migrate existing
-- data, and drop the old tables.

-- 1. Create the unified predictions table.
CREATE TABLE IF NOT EXISTS public.predictions (
    id        BIGSERIAL    PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT now(),
    band       TEXT         NOT NULL,
    model_slug TEXT         NOT NULL,
    reference_date DATE     NOT NULL,
    predictions  JSONB      NOT NULL,
    top_k      INT          NOT NULL,
    model_version TEXT      NOT NULL,
    collected_at TIMESTAMPTZ,
    predicted_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Unique constraint: one prediction row per (band, model_slug, reference_date, model_version).
ALTER TABLE public.predictions
    ADD CONSTRAINT ux_predictions_band_slug_ref_version
    UNIQUE (band, model_slug, reference_date, model_version);

-- 3. Query index matching the previous per-table pattern.
CREATE INDEX ix_predictions_band_refdate
    ON public.predictions (band, reference_date DESC, predicted_at DESC);

-- Additional index for slug-scoped queries.
CREATE INDEX ix_predictions_band_slug_refdate
    ON public.predictions (band, model_slug, reference_date DESC, predicted_at DESC);

-- 4. Enable RLS.
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

-- Public read policy (anon can SELECT).
CREATE POLICY predictions_public_read ON public.predictions
    FOR SELECT TO anon USING (true);

-- Service role full access.
CREATE POLICY predictions_service_all ON public.predictions
    FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 5. Migrate data from the three legacy tables.
INSERT INTO public.predictions (created_at, band, model_slug, reference_date, predictions, top_k, model_version, collected_at, predicted_at)
SELECT created_at, band, 'notebook', reference_date, predictions, top_k, model_version, collected_at, predicted_at
FROM public.predictions_notebook
ON CONFLICT (band, model_slug, reference_date, model_version) DO NOTHING;

INSERT INTO public.predictions (created_at, band, model_slug, reference_date, predictions, top_k, model_version, collected_at, predicted_at)
SELECT created_at, band, 'deal', reference_date, predictions, top_k, model_version, collected_at, predicted_at
FROM public.predictions_deal
ON CONFLICT (band, model_slug, reference_date, model_version) DO NOTHING;

INSERT INTO public.predictions (created_at, band, model_slug, reference_date, predictions, top_k, model_version, collected_at, predicted_at)
SELECT created_at, band, 'ckplus', reference_date, predictions, top_k, model_version, collected_at, predicted_at
FROM public.predictions_ckplus
ON CONFLICT (band, model_slug, reference_date, model_version) DO NOTHING;

-- 6. Fix prediction_songs unique constraint to include model_slug.
--    Drop the old constraint and create the corrected one.
ALTER TABLE public.prediction_songs
    DROP CONSTRAINT IF EXISTS prediction_songs_band_model_version_reference_date_rank_key;

ALTER TABLE public.prediction_songs
    ADD CONSTRAINT prediction_songs_band_slug_version_date_rank_key
    UNIQUE (band, model_slug, model_version, reference_date, rank);
