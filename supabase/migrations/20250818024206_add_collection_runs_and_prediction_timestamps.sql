create table if not exists public.collection_runs (
  id bigserial primary key,
  created_at timestamptz default now(),
  band text not null
);
alter table public.goose_notebook_predictions add column if not exists collected_at timestamptz;
alter table public.goose_notebook_predictions add column if not exists predicted_at timestamptz default now();;
