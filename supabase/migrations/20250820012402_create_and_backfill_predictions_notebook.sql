begin;

create table if not exists public.predictions_notebook (
  id bigserial primary key,
  created_at timestamptz default now(),
  band text not null,
  reference_date date not null,
  predictions jsonb not null,
  top_k int not null,
  model_version text not null default 'notebook_v1',
  collected_at timestamptz,
  predicted_at timestamptz default now()
);

create unique index if not exists ux_predictions_notebook_band_ref_model
  on public.predictions_notebook (band, reference_date, model_version);

create index if not exists ix_predictions_notebook_band_refdate
  on public.predictions_notebook (band, reference_date desc, predicted_at desc);

insert into public.predictions_notebook (band, reference_date, predictions, top_k, model_version, collected_at, predicted_at)
select band, reference_date, predictions, top_k, model_version, collected_at, predicted_at
from public.goose_notebook_predictions
on conflict (band, reference_date, model_version) do nothing;

commit;;
