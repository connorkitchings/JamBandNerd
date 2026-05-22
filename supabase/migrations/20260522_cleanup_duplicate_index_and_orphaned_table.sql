-- Migration: Cleanup duplicate index and orphaned table
-- Date: 2026-05-22
-- Purpose: Remove duplicate goose_setlists_raw index and unused wsp_shows_upcoming table

-- Duplicate index: idx_goose_setlists_raw_show_id (created 20250817) duplicates
-- goose_setlists_raw_show_id_idx (created 20260321). Both index (show_id).
DROP INDEX IF EXISTS public.idx_goose_setlists_raw_show_id;

-- Orphaned table: wsp_shows_upcoming was created in 20251027 but no Python or
-- TypeScript code reads or writes it. UM uses um_upcoming_shows; WSP does not.
DROP TABLE IF EXISTS public.wsp_shows_upcoming CASCADE;
