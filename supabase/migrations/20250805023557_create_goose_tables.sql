CREATE TABLE public.goose_setlists (
    uniqueid TEXT PRIMARY KEY,
    show_id INTEGER,
    song_id INTEGER,
    setnumber INTEGER,
    position INTEGER,
    tracktime TEXT,
    transition_id INTEGER,
    isreprise BOOLEAN,
    isjam BOOLEAN,
    footnote TEXT,
    isjamchart BOOLEAN,
    jamchart_notes TEXT,
    soundcheck BOOLEAN,
    isverified BOOLEAN,
    isrecommended BOOLEAN
);

CREATE TABLE public.goose_transitions (
    transition_id INTEGER PRIMARY KEY,
    transition TEXT
);

ALTER TABLE public.goose_setlists ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access" ON public.goose_setlists FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE public.goose_transitions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public access" ON public.goose_transitions FOR ALL USING (true) WITH CHECK (true);;
