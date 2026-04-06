CREATE TABLE public.songs (
    song_id integer NOT NULL PRIMARY KEY,
    song_name text,
    author text,
    is_original boolean,
    lyrics text,
    notes text,
    debut_date text,
    last_played text,
    times_played integer,
    gap integer
);;
