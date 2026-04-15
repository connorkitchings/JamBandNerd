# Fix Daily Pipeline Failures

## Root Cause

Migration ordering conflict in `supabase/migrations/`:

- `20260413_consoldiate_predictions_table.sql` **creates** `public.predictions`
- `20260413_drop_legacy_tables.sql` **drops** `public.predictions CASCADE` (line 4)

Supabase applies alphabetically: `consoldiate` < `drop_legacy`, so the DROP kills the newly created table.

## Steps

### 1. Fix migration file

**File**: `supabase/migrations/20260413_drop_legacy_tables.sql`

Remove line 4 (`DROP TABLE IF EXISTS public.predictions CASCADE;`). The old football-era `predictions` table (if it still existed) is superseded by the consolidation migration. The DROP is now harmful.

Change:
```sql
-- Drop legacy football tables (pre-JamBandNerd pivot)
DROP TABLE IF EXISTS public.games CASCADE;
DROP TABLE IF EXISTS public.plays CASCADE;
DROP TABLE IF EXISTS public.predictions CASCADE;
```

To:
```sql
-- Drop legacy football tables (pre-JamBandNerd pivot)
DROP TABLE IF EXISTS public.games CASCADE;
DROP TABLE IF EXISTS public.plays CASCADE;
```

### 2. Verify live Supabase state

Run a check script to confirm:
- Does `public.predictions` exist? (Likely yes — the 19:39 goose run succeeded)
- Do legacy tables (`predictions_notebook`, `predictions_deal`, `predictions_ckplus`) still exist?
- Does the schema match the consolidation migration?

Command:
```bash
uv run python scripts/admin/get_schemas.py
```

Or use `supabase` CLI if available:
```bash
supabase db diff --schema public
```

### 3. Re-apply consolidation migration if needed

If `predictions` table is missing or incomplete, re-run:
```bash
supabase db push
# or manually apply 20260413_consoldiate_predictions_table.sql
```

If legacy tables are already gone (dropped by `20260415_drop_legacy_prediction_tables.sql`), the INSERT...SELECT statements in the consolidation will be no-ops, but the CREATE TABLE and constraints will still apply.

### 4. Run quality gates

```bash
npm run verify:python
npm run verify:docs
```

### 5. (Separate) Investigate Fantasy Goose failure

The 20:15 UTC Fantasy Goose run failed with:
```
RuntimeError: Fantasy Goose submission did not appear in My Picks for 04/14/2026 - War Memorial Auditorium - Fort Lauderdale, FL.
```

This is a submission verification issue — the pick may have been submitted but the verification check couldn't find it. Check `src/jambandnerd/integrations/fantasy_goose.py:482` for the verification logic.

## Branch

Create a feature branch (e.g., `fix/migration-predictions-drop`) — never work on `main`.
