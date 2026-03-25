CREATE TABLE public.setlists (
    uniqueid text NOT NULL PRIMARY KEY,
    showid integer,
    set_number integer,
    song_id integer,
    position integer,
    is_segue boolean,
    notes text
);;
