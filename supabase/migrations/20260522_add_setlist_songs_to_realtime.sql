-- Migration: Add setlist_prediction_songs to realtime publication
-- Date: 2026-05-22
-- Purpose: Enable Supabase Realtime for setlist_prediction_songs
-- Required for the LiveTracker client component to receive live updates

ALTER PUBLICATION supabase_realtime ADD TABLE setlist_prediction_songs;
