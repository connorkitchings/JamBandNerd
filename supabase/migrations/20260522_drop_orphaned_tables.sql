-- Migration: Drop orphaned and superseded tables
-- Date: 2026-05-22
-- Purpose: Clean up tables that are no longer referenced by active code

-- Orphaned Goose legacy tables (policies dropped in 20260402, tables never dropped)
DROP TABLE IF EXISTS public.goose_setlists CASCADE;
DROP TABLE IF EXISTS public.goose_transitions CASCADE;

-- Orphaned Cosmic tables (created but never used, only cosmic_country_* was active and dropped)
DROP TABLE IF EXISTS public.cosmic_shows_raw CASCADE;
DROP TABLE IF EXISTS public.cosmic_setlists_raw CASCADE;
DROP TABLE IF EXISTS public.cosmic_songs_raw CASCADE;
DROP TABLE IF EXISTS public.cosmic_venues_raw CASCADE;

-- Superseded by setlist_results (no Python code references this table)
DROP TABLE IF EXISTS public.historical_prediction_runs CASCADE;

-- Superseded by setlist_predictions/setlist_prediction_songs (legacy unified table with model_slug)
DROP TABLE IF EXISTS public.predictions CASCADE;
DROP TABLE IF EXISTS public.prediction_songs CASCADE;

-- Superseded by setlist_accuracy (legacy wide-format accuracy table)
DROP TABLE IF EXISTS public.accuracy_per_show CASCADE;
