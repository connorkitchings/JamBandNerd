-- Keep setlist_accuracy aligned with the setlist_* product-facing date contract.
-- show_date is retained for compatibility; target_show_date is the website-facing
-- selector shared by setlist_predictions and setlist_results.

alter table public.setlist_accuracy
    add column if not exists target_show_date date;

update public.setlist_accuracy
set target_show_date = show_date
where target_show_date is null;

alter table public.setlist_accuracy
    alter column target_show_date set not null;

create index if not exists setlist_accuracy_band_target_date_idx
    on public.setlist_accuracy (
        band,
        target_show_date desc
    );
