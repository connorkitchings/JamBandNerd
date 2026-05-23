-- Migration: Add FK indexes for setlist tables
-- Date: 2026-05-22
-- Purpose: Improve join performance for replay lineage and prediction-song lookups

-- FK index for setlist_prediction_songs -> setlist_predictions join
CREATE INDEX IF NOT EXISTS setlist_prediction_songs_prediction_run_id_idx
    ON public.setlist_prediction_songs (prediction_run_id);

-- Composite index for replay lineage queries (accuracy -> results join)
CREATE INDEX IF NOT EXISTS setlist_accuracy_prediction_run_id_idx
    ON public.setlist_accuracy (prediction_run_id);
