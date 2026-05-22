CREATE INDEX IF NOT EXISTS setlist_accuracy_band_show_date_idx
    ON public.setlist_accuracy (band, show_date DESC);
