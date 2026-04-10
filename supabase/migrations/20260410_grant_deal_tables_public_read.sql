begin;

-- Grant public read access to predictions_deal and accuracy_deal.
-- These tables were created alongside predictions_ckplus / accuracy_ckplus but were
-- omitted from the public_read_tables list in the 20260402193000 RLS migration.
-- Deal is now the promoted second model, replacing CK+.

do $$
declare
    t text;
    deal_public_tables text[] := array[
        'predictions_deal',
        'accuracy_deal'
    ];
begin
    foreach t in array deal_public_tables loop
        if to_regclass(format('public.%I', t)) is not null then
            execute format('alter table public.%I enable row level security', t);
            execute format('drop policy if exists "Public read access" on public.%I', t);
            execute format(
                'create policy "Public read access" on public.%I for select using (true)',
                t
            );
        end if;
    end loop;
end $$;

commit;
