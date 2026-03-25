# Session Log: 2026-03-25 - Replay Backfill Attempt Blocked By Missing Remote Migration

## Goal

Run the recent-50 replay backfill across all bands and both models using the
new retained historical-run path.

## Commands run

- `set -a; source .env; set +a; uv run python scripts/rebuild_derived_data.py --band all --recent-shows 50 --aggregate-shows 100`
- `set -a; source .env; set +a; uv run python - <<'PY' ... client.table('historical_prediction_runs').select('*').limit(1).execute() ... PY`
- `set -a; source .env; set +a; uv run python - <<'PY' ... client.table('accuracy_per_show').select('prediction_run_id').limit(1).execute() ... PY`

## Outcome

- The rebuild started successfully for `GOOSE/NOTEBOOK`
- Live prediction regeneration succeeded
- The backfill failed on the first historical-run insert

## Blocker

The connected Supabase project does not have the replay-lineage migration
applied:

- `historical_prediction_runs` does not exist
- `accuracy_per_show.prediction_run_id` does not exist

This means the code path is ready, but the remote database is not.

## Next Step

Apply the remote migration(s) first, then rerun:

```bash
uv run python scripts/rebuild_derived_data.py --band all --recent-shows 50 --aggregate-shows 100
```

Relevant migration files:

- `supabase/migrations/20260322_accuracy_per_show_show_id_text.sql`
- `supabase/migrations/20260325_create_historical_prediction_runs.sql`
