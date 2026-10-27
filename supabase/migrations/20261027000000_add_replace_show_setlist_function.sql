-- Atomic per-show setlist replacement for the weekly correction sweep.
--
-- Replaces the client-side "delete all rows, then insert one by one" flow with
-- a single transaction. Guards:
--   * `p_band` must be in the whitelist (it selects the table; no other input
--     reaches dynamic SQL except as a quoted identifier or bound parameter).
--   * Every replacement row must belong to `p_show_id`.
--   * The replacement must have at least 1 row and may not shrink the stored
--     setlist by more than 50%.
-- Executable by `service_role` only.

begin;

create or replace function public.replace_show_setlist(
    p_band text,
    p_show_id text,
    p_rows jsonb
)
returns jsonb
language plpgsql
security invoker
set search_path = public, pg_temp
as $$
declare
    v_table text;
    v_columns text;
    v_old_count integer;
    v_new_count integer;
    v_deleted integer;
begin
    v_table := case p_band
        when 'goose' then 'goose_setlists_raw'
        when 'eggy'  then 'eggy_setlists_raw'
        when 'phish' then 'phish_setlists_raw'
        when 'wsp'   then 'wsp_setlists_raw'
        when 'billy' then 'billy_setlists_raw'
        when 'um'    then 'um_setlists_raw'
        else null
    end;
    if v_table is null then
        raise exception 'replace_show_setlist: unsupported band';
    end if;

    if p_show_id is null or btrim(p_show_id) = '' then
        raise exception 'replace_show_setlist: show id is required';
    end if;
    if p_rows is null or jsonb_typeof(p_rows) <> 'array' then
        raise exception 'replace_show_setlist: rows must be a JSON array';
    end if;

    v_new_count := jsonb_array_length(p_rows);
    if v_new_count = 0 then
        raise exception 'replace_show_setlist: refusing empty replacement';
    end if;

    if exists (
        select 1
        from jsonb_array_elements(p_rows) as r(row_data)
        where jsonb_typeof(r.row_data) <> 'object'
           or (r.row_data ->> 'show_id') is distinct from p_show_id
    ) then
        raise exception 'replace_show_setlist: every row must belong to the target show';
    end if;

    execute format('select count(*) from public.%I where show_id::text = $1', v_table)
        into v_old_count
        using p_show_id;

    if v_new_count * 2 < v_old_count then
        raise exception
            'replace_show_setlist: replacement shrinks setlist by more than 50%% (% -> %)',
            v_old_count, v_new_count;
    end if;

    -- Insert only columns that exist on the table and are present in the
    -- payload; never `id` (generated). Missing keys fall back to defaults.
    select string_agg(format('%I', c.column_name), ', ' order by c.ordinal_position)
      into v_columns
      from information_schema.columns c
     where c.table_schema = 'public'
       and c.table_name = v_table
       and c.column_name <> 'id'
       and exists (
           select 1 from jsonb_object_keys(p_rows -> 0) k where k = c.column_name
       );

    if v_columns is null then
        raise exception 'replace_show_setlist: no insertable columns in payload';
    end if;

    execute format('delete from public.%I where show_id::text = $1', v_table)
        using p_show_id;
    get diagnostics v_deleted = row_count;

    execute format(
        'insert into public.%1$I (%2$s) select %2$s from jsonb_populate_recordset(null::public.%1$I, $1)',
        v_table, v_columns
    ) using p_rows;

    return jsonb_build_object('deleted', v_deleted, 'inserted', v_new_count);
end;
$$;

revoke all on function public.replace_show_setlist(text, text, jsonb) from public;
revoke all on function public.replace_show_setlist(text, text, jsonb) from anon;
revoke all on function public.replace_show_setlist(text, text, jsonb) from authenticated;
grant execute on function public.replace_show_setlist(text, text, jsonb) to service_role;

commit;
