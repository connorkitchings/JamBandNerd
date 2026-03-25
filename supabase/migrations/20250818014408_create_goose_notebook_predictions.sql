create table if not exists public.goose_notebook_predictions (
  id bigserial primary key,
  created_at timestamptz default now(),
  band text not null default 'goose',
  reference_show_index integer not null,
  reference_date date not null,
  predictions jsonb not null,
  top_k integer not null,
  model_version text not null default 'notebook_v1'
);
create index if not exists idx_goose_notebook_predictions_ref on public.goose_notebook_predictions (reference_date, reference_show_index);
;
