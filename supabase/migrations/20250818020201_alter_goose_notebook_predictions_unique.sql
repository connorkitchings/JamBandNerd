alter table public.goose_notebook_predictions drop column if exists reference_show_index;
create unique index if not exists uq_goose_notebook_predictions_band_date_version
  on public.goose_notebook_predictions (band, reference_date, model_version);
;
