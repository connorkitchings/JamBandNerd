begin;

do $$
declare
    table_name text;
    protected_tables text[] := array[
        'pipeline_metadata',
        'collection_runs',
        'bands',
        'prediction_songs',
        'predictions_notebook',
        'predictions_deal',
        'predictions_ckplus',
        'accuracy_deal',
        'accuracy_ckplus',
        'accuracy_per_show',
        'notebook_accuracy',
        'historical_prediction_runs',
        'goose_notebook_predictions',
        'goose_setlists',
        'goose_transitions',
        'goose_songs_raw',
        'goose_shows_raw',
        'goose_setlists_raw',
        'goose_venues_raw',
        'phish_songs_raw',
        'phish_shows_raw',
        'phish_setlists_raw',
        'phish_venues_raw',
        'wsp_songs_raw',
        'wsp_shows_raw',
        'wsp_setlists_raw',
        'wsp_shows_upcoming',
        'um_songs_raw',
        'um_venues_raw',
        'um_shows_raw',
        'um_setlists_raw',
        'um_upcoming_shows',
        'billy_songs_raw',
        'billy_shows_raw',
        'billy_setlists_raw',
        'eggy_songs_raw',
        'eggy_shows_raw',
        'eggy_venues_raw',
        'eggy_setlists_raw',
        'cosmic_shows_raw',
        'cosmic_setlists_raw',
        'cosmic_songs_raw',
        'cosmic_venues_raw'
    ];
    public_read_tables text[] := array[
        'bands',
        'prediction_songs',
        'predictions_notebook',
        'predictions_ckplus',
        'accuracy_per_show',
        'historical_prediction_runs',
        'goose_shows_raw',
        'goose_setlists_raw',
        'phish_shows_raw',
        'phish_setlists_raw',
        'wsp_shows_raw',
        'wsp_setlists_raw',
        'wsp_shows_upcoming',
        'um_shows_raw',
        'um_setlists_raw',
        'um_upcoming_shows',
        'billy_shows_raw',
        'billy_setlists_raw',
        'eggy_shows_raw',
        'eggy_setlists_raw'
    ];
begin
    foreach table_name in array array['pipeline_metadata', 'goose_setlists', 'goose_transitions'] loop
        if to_regclass(format('public.%I', table_name)) is not null then
            execute format('drop policy if exists "Allow public access" on public.%I', table_name);
        end if;
    end loop;

    foreach table_name in array protected_tables loop
        if to_regclass(format('public.%I', table_name)) is not null then
            execute format('alter table public.%I enable row level security', table_name);
        end if;
    end loop;

    foreach table_name in array public_read_tables loop
        if to_regclass(format('public.%I', table_name)) is not null then
            execute format('drop policy if exists "Public read access" on public.%I', table_name);
            execute format(
                'create policy "Public read access" on public.%I for select to anon, authenticated using (true)',
                table_name
            );
        end if;
    end loop;
end
$$;

commit;
