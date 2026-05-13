-- Denormalize live prediction metadata onto the per-song projection table.
-- This keeps realtime/site reads scoped by the show being predicted instead of
-- relying on reference_date, which is the model cutoff.

alter table public.setlist_prediction_songs
    add column if not exists target_show_date date,
    add column if not exists reference_date date,
    add column if not exists generated_at timestamptz,
    add column if not exists top_k integer;

update public.setlist_prediction_songs songs
set
    target_show_date = runs.target_show_date,
    reference_date = runs.reference_date,
    generated_at = runs.generated_at,
    top_k = runs.top_k
from public.setlist_predictions runs
where songs.prediction_run_id = runs.id
  and (
      songs.target_show_date is null
      or songs.reference_date is null
      or songs.generated_at is null
      or songs.top_k is null
  );

alter table public.setlist_prediction_songs
    alter column target_show_date set not null,
    alter column reference_date set not null,
    alter column generated_at set not null,
    alter column top_k set not null;

alter table public.setlist_prediction_songs
    add constraint setlist_prediction_songs_top_k_positive
    check (top_k > 0) not valid;

alter table public.setlist_prediction_songs
    validate constraint setlist_prediction_songs_top_k_positive;

create index if not exists setlist_predictions_band_target_date_generated_idx
    on public.setlist_predictions (
        band,
        target_show_date desc,
        generated_at desc
    );

create index if not exists setlist_results_band_target_date_idx
    on public.setlist_results (
        band,
        target_show_date desc
    );

create index if not exists setlist_prediction_songs_site_lookup_idx
    on public.setlist_prediction_songs (
        band,
        model_version,
        target_show_key,
        rank
    );
