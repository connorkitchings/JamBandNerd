-- Restrict schema introspection to server-side contexts.
-- Apply this in Supabase SQL Editor or through the Supabase CLI.

create or replace function public.get_table_schema(p_table_name text)
returns table (column_name text, data_type text, is_nullable text)
language sql
security definer
set search_path = public
as $$
  select column_name, data_type, is_nullable
  from information_schema.columns
  where table_schema = 'public' and table_name = p_table_name
  order by ordinal_position;
$$;

revoke execute on function public.get_table_schema(text) from anon, authenticated;
grant execute on function public.get_table_schema(text) to service_role;
