# Supabase API Interaction Guide

This document provides the standard instructions for interacting with the project's Supabase
backend via its API.

## 1. API Credentials

All API requests require a URL and an API Key. These can be found in your Supabase project's
dashboard under **Settings > API**.

- **Project URL**: The base URL for all API requests (e.g., `https://<project-ref>.supabase.co`).
- **API Keys**:
  - `anon` (public): A key that is safe for client-side use. It respects all Row Level Security
    (RLS) policies.
  - `service_role` (secret): A key that bypasses all RLS policies. This key must only be used in a
    secure server environment and should never be exposed publicly.

## 2. Executing Queries

Supabase uses PostgREST to provide a RESTful interface to your PostgreSQL database.

### Direct Table Access

You can perform standard RESTful operations (GET, POST, PATCH, DELETE) on your tables.

#### Endpoint

`/rest/v1/<table_name>`

#### Example: GET all rows

```bash
curl 'https://<project-ref>.supabase.co/rest/v1/my_table?select=*' \
-H "apikey: <your_api_key>" \
-H "Authorization: Bearer <your_api_key>"
```

### Executing SQL via RPC

For more complex operations or to run raw SQL, the recommended approach is to create a function in
the database and call it as a Remote Procedure Call (RPC).

#### Step 1: Define the SQL Function (Example: Table Schema RPC)

In the Supabase dashboard's SQL Editor, define a function.

```sql
create or replace function public.get_table_schema(p_table_name text)
returns table (column_name text, data_type text, is_nullable text)
language sql as $$
  select column_name, data_type, is_nullable
  from information_schema.columns
  where table_schema = 'public' and table_name = p_table_name
  order by ordinal_position;
$$;
revoke execute on function public.get_table_schema(text) from anon, authenticated;
grant execute on function public.get_table_schema(text) to service_role;
```

#### Step 2: Call the Function via the API

Use a `POST` request to the `/rpc/<function_name>` endpoint.

##### RPC Endpoint

`/rpc/<function_name>`

##### Example: Calling create_my_table

```bash
curl -X POST 'https://<project-ref>.supabase.co/rest/v1/rpc/create_my_table' \
-H "apikey: <your_api_key>" \
-H "Authorization: Bearer <your_api_key>" \
-H "Content-Type: application/json"
```

## 3. Required Headers

Every API request must include the following headers:

- `apikey`: Your Supabase `anon` or `service_role` key.
- `Authorization`: The value must be `Bearer <your_api_key>`, using the same key as the `apikey` header.
- `Content-Type`: Typically `application/json` for `POST` or `PATCH` requests.
