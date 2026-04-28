# Supabase Local Development

This guide covers running the JamBandNerd Supabase stack locally for
development and testing.

## Prerequisites

- [Supabase CLI](https://supabase.com/docs/guides/cli) installed
- Docker running

## Setup

1. **Start the local Supabase stack:**

   ```bash
   supabase start
   ```

   This reads `supabase/config.toml` and applies all 68+ migrations from
   `supabase/migrations/` to a local Postgres instance.

2. **Note the output URLs and keys:**

   The CLI prints connection details on startup. Use these for your local
   `.env` and `apps/web/.env.local`:

   - `API URL` → `SUPABASE_URL`
   - `anon key` → `SUPABASE_ANON_KEY` (website)
   - `service_role key` → `SUPABASE_SERVICE_ROLE_KEY` (pipeline)

3. **Configure environment files:**

   ```bash
   # Pipeline .env
   cat > .env << 'EOF'
   SUPABASE_URL=http://127.0.0.1:54321
   SUPABASE_SERVICE_ROLE_KEY=<service_role key from supabase start>
   EOF

   # Website .env.local
   cp apps/web/.env.local.example apps/web/.env.local
   # Fill in SUPABASE_URL and SUPABASE_ANON_KEY
   ```

## Applying Migrations

After pulling new migrations from the remote or writing new ones:

```bash
supabase db reset
```

This tears down and recreates the local database, applying all migrations in
order.

To apply migrations without resetting:

```bash
supabase migration up
```

## Seeding Data

The local stack does not ship with seed data by default. To populate test data:

1. Run the collection scripts against the local Supabase instance:

   ```bash
   uv run python scripts/run_goose_collection.py
   ```

2. Or create a `supabase/seed.sql` file with INSERT statements and run
   `supabase db reset`.

## Useful Commands

```bash
# Check local stack status
supabase status

# Stop the local stack
supabase stop

# Stop and remove all data
supabase stop --no-backup

# Open Supabase Studio (local GUI)
supabase studio

# Generate a new migration from local schema changes
supabase db diff -s public -f my_migration_name

# Link to remote project for diffing
supabase link --project-ref <project-ref>
```

## Schema Reference

The canonical schema documentation lives in:

- `docs/reference/specifications/data_strategy.md` — data contract and storage strategy
- `docs/reference/schemas/unified_tables.md` — current split prediction table DDL
- `docs/reference/specifications/predictions_schema.md` — prediction/accuracy schema details
- `docs/reference/specifications/database.md` — database utility module reference

## Notes

- The local stack uses Postgres 17 (configured in `supabase/config.toml`).
- RLS policies from migrations are applied locally, so `anon` reads work the
  same as in production.
- The `collection_runs` table is used by the pipeline for operational tracking
  and is not documented in the main schema docs.
