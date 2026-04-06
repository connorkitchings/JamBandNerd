create index if not exists goose_shows_raw_show_date_idx on public.goose_shows_raw(show_date);
create index if not exists phish_shows_raw_show_date_idx on public.phish_shows_raw(show_date);
create index if not exists wsp_shows_raw_show_date_idx on public.wsp_shows_raw(show_date);
create index if not exists billy_shows_raw_show_date_idx on public.billy_shows_raw(show_date);
create index if not exists um_shows_raw_show_date_idx on public.um_shows_raw(show_date);
create index if not exists billy_setlists_raw_show_id_idx on public.billy_setlists_raw(show_id);
create index if not exists um_setlists_raw_show_id_idx on public.um_setlists_raw(show_id);
;
