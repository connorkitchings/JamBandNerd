-- Migration: Create wsp_venues_raw table
-- Date: 2026-05-22
-- Purpose: Create missing wsp_venues_raw table referenced by WSP collector code
-- Schema derived from src/jambandnerd/data_collection/wsp/normalizer.py:normalize_venues()

CREATE TABLE public.wsp_venues_raw (
    venue_id text NOT NULL PRIMARY KEY,
    venue_name text,
    city text,
    state text,
    country text,
    zip text,
    capacity integer DEFAULT 0,
    slug text,
    source_hash text NOT NULL,
    created_at timestamp with time zone,
    updated_at timestamp with time zone
);

ALTER TABLE public.wsp_venues_raw ENABLE ROW LEVEL SECURITY;

CREATE POLICY "wsp_venues_raw_service_all" ON public.wsp_venues_raw
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE INDEX wsp_venues_raw_venue_name_idx ON public.wsp_venues_raw (venue_name);
