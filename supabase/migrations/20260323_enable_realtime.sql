-- Enable Realtime for the prediction_songs table
-- This allows the Next.js frontend to automatically refresh when the run_live_tracker.py script pushes updates.
ALTER PUBLICATION supabase_realtime ADD TABLE prediction_songs;
