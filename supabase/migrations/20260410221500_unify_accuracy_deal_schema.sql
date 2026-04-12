begin;

create table if not exists public.accuracy_deal (
  id bigserial primary key,
  created_at timestamptz default now(),
  band text,
  model_version text,
  window_start date,
  window_end date,
  num_shows integer,
  evaluated_at timestamptz,
  k10_hit_rate double precision,
  k10_avg_matches double precision,
  k10_precision double precision,
  k10_recall double precision,
  k10_f1 double precision,
  k25_hit_rate double precision,
  k25_avg_matches double precision,
  k25_precision double precision,
  k25_recall double precision,
  k25_f1 double precision,
  k50_hit_rate double precision,
  k50_avg_matches double precision,
  k50_precision double precision,
  k50_recall double precision,
  k50_f1 double precision
);

alter table public.accuracy_deal
  add column if not exists num_shows integer,
  add column if not exists evaluated_at timestamptz,
  add column if not exists k10_hit_rate double precision,
  add column if not exists k10_avg_matches double precision,
  add column if not exists k10_precision double precision,
  add column if not exists k10_recall double precision,
  add column if not exists k10_f1 double precision,
  add column if not exists k25_hit_rate double precision,
  add column if not exists k25_avg_matches double precision,
  add column if not exists k25_precision double precision,
  add column if not exists k25_recall double precision,
  add column if not exists k25_f1 double precision,
  add column if not exists k50_hit_rate double precision,
  add column if not exists k50_avg_matches double precision,
  add column if not exists k50_precision double precision,
  add column if not exists k50_recall double precision,
  add column if not exists k50_f1 double precision;

do $$
begin
  if exists (
    select 1
    from information_schema.columns
    where table_schema = 'public'
      and table_name = 'accuracy_deal'
      and column_name = 'k_value'
  ) then
    create temp table accuracy_deal_legacy_rollup on commit drop as
    select
      max(created_at) as created_at,
      band,
      model_version,
      window_start,
      window_end,
      null::integer as num_shows,
      coalesce(max(created_at), now()) as evaluated_at,
      max(hit_rate) filter (where k_value = 10)::double precision as k10_hit_rate,
      max(avg_matches) filter (where k_value = 10)::double precision as k10_avg_matches,
      max(precision_score) filter (where k_value = 10)::double precision as k10_precision,
      max(recall_score) filter (where k_value = 10)::double precision as k10_recall,
      max(f1_score) filter (where k_value = 10)::double precision as k10_f1,
      max(hit_rate) filter (where k_value = 25)::double precision as k25_hit_rate,
      max(avg_matches) filter (where k_value = 25)::double precision as k25_avg_matches,
      max(precision_score) filter (where k_value = 25)::double precision as k25_precision,
      max(recall_score) filter (where k_value = 25)::double precision as k25_recall,
      max(f1_score) filter (where k_value = 25)::double precision as k25_f1,
      max(hit_rate) filter (where k_value = 50)::double precision as k50_hit_rate,
      max(avg_matches) filter (where k_value = 50)::double precision as k50_avg_matches,
      max(precision_score) filter (where k_value = 50)::double precision as k50_precision,
      max(recall_score) filter (where k_value = 50)::double precision as k50_recall,
      max(f1_score) filter (where k_value = 50)::double precision as k50_f1
    from public.accuracy_deal
    group by band, model_version, window_start, window_end;

    truncate table public.accuracy_deal;

    insert into public.accuracy_deal (
      created_at,
      band,
      model_version,
      window_start,
      window_end,
      num_shows,
      evaluated_at,
      k10_hit_rate,
      k10_avg_matches,
      k10_precision,
      k10_recall,
      k10_f1,
      k25_hit_rate,
      k25_avg_matches,
      k25_precision,
      k25_recall,
      k25_f1,
      k50_hit_rate,
      k50_avg_matches,
      k50_precision,
      k50_recall,
      k50_f1
    )
    select
      created_at,
      band,
      model_version,
      window_start,
      window_end,
      num_shows,
      evaluated_at,
      k10_hit_rate,
      k10_avg_matches,
      k10_precision,
      k10_recall,
      k10_f1,
      k25_hit_rate,
      k25_avg_matches,
      k25_precision,
      k25_recall,
      k25_f1,
      k50_hit_rate,
      k50_avg_matches,
      k50_precision,
      k50_recall,
      k50_f1
    from accuracy_deal_legacy_rollup;
  end if;
end $$;

alter table public.accuracy_deal
  drop constraint if exists accuracy_deal_band_model_version_window_key,
  drop constraint if exists accuracy_deal_band_model_version_window_start_window_end_key;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'accuracy_deal_band_model_version_window_start_window_end_key'
      and conrelid = 'public.accuracy_deal'::regclass
  ) then
    alter table public.accuracy_deal
      add constraint accuracy_deal_band_model_version_window_start_window_end_key
      unique (band, model_version, window_start, window_end);
  end if;
end $$;

alter table public.accuracy_deal
  drop column if exists k_value,
  drop column if exists hit_rate,
  drop column if exists avg_matches,
  drop column if exists precision_score,
  drop column if exists recall_score,
  drop column if exists f1_score,
  drop column if exists auc;

create index if not exists idx_accuracy_deal_window
  on public.accuracy_deal (band, model_version, window_end);

commit;
