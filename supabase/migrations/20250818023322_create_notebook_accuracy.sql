create table if not exists public.notebook_accuracy (
  id bigserial primary key,
  created_at timestamptz default now(),
  band text not null,
  model_version text not null default 'notebook_v1',
  window_start date not null,
  window_end date not null,
  num_shows integer not null,
  k10_hit_rate double precision not null,
  k10_avg_matches double precision not null,
  k10_precision double precision not null,
  k10_recall double precision not null,
  k10_f1 double precision not null,
  k25_hit_rate double precision not null,
  k25_avg_matches double precision not null,
  k25_precision double precision not null,
  k25_recall double precision not null,
  k25_f1 double precision not null,
  k50_hit_rate double precision not null,
  k50_avg_matches double precision not null,
  k50_precision double precision not null,
  k50_recall double precision not null,
  k50_f1 double precision not null
);
create index if not exists idx_notebook_accuracy_window on public.notebook_accuracy (band, model_version, window_end);
;
