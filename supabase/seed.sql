INSERT INTO public.bands (slug, display_name, shows_table, id_column, is_active)
VALUES
    ('eggy', 'Eggy', 'eggy_shows_raw', 'show_id', false),
    ('billy', 'Billy Strings', 'billy_shows_raw', 'show_id', true),
    ('goose', 'Goose', 'goose_shows_raw', 'show_id', true),
    ('phish', 'Phish', 'phish_shows_raw', 'show_id', true),
    ('wsp', 'Widespread Panic', 'wsp_shows_raw', 'show_id', true),
    ('um', 'Umphrey''s McGee', 'um_shows_raw', 'show_id', true)
ON CONFLICT (slug) DO NOTHING;
