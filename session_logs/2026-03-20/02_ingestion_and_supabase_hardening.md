# 2026-03-20 Session Log 02

## Goal

- Implement the ingestion and Supabase hardening plan from the live schema review.

## Constraints

- Do not mutate the live Supabase project directly from this session.
- Preserve canonical entrypoints such as `scripts/run_optimized_pipeline.py`.
- Keep the website on server-side Supabase reads, but remove service-role ambiguity from its env contract.

## Commands Run

```bash
git checkout -b chore-ingestion-supabase-hardening
uv run black src/jambandnerd/db src/jambandnerd/data_collection/wsp scripts/run_goose_collection.py scripts/run_eggy_collection.py scripts/run_phish_collection.py scripts/run_billy_collection.py scripts/run_um_collection.py scripts/generate_predictions.py scripts/save_aggregate_accuracy.py tests/test_db.py tests/test_db_operations.py tests/pipeline/test_band_collection_regressions.py
uv run ruff check --fix src/jambandnerd/db src/jambandnerd/data_collection/wsp scripts/run_goose_collection.py scripts/run_eggy_collection.py scripts/run_phish_collection.py scripts/run_billy_collection.py scripts/run_um_collection.py scripts/generate_predictions.py scripts/save_aggregate_accuracy.py tests/test_db.py tests/test_db_operations.py tests/pipeline/test_band_collection_regressions.py
uv run ruff check src/jambandnerd/db src/jambandnerd/data_collection/wsp scripts/run_goose_collection.py scripts/run_eggy_collection.py scripts/run_phish_collection.py scripts/run_billy_collection.py scripts/run_um_collection.py scripts/generate_predictions.py scripts/save_aggregate_accuracy.py tests/test_db.py tests/test_db_operations.py tests/pipeline/test_band_collection_regressions.py
uv run pytest tests/test_db.py tests/test_db_operations.py tests/pipeline/test_band_collection_regressions.py tests/pipeline/test_run_optimized_pipeline.py
npm run lint:web
npm run build:web
SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... uv run python scripts/run_optimized_pipeline.py --band goose --skip-accuracy
curl http://localhost:3000/?band=goose&model=notebook
curl http://localhost:3000/compare?band=goose
curl http://localhost:3000/explorer?band=goose&model=notebook
curl http://localhost:3000/last-show?band=goose
curl http://localhost:3000/performance?band=goose&model=notebook
npm run lint:web
npm run build:web
```

## Files Changed

- Added shared DB write-preparation and targeted lookup helpers in `src/jambandnerd/db/operations.py`.
- Switched Goose, Eggy, Phish, Billy, UM, and WSP ingestion paths onto the shared validation/upsert flow.
- Replaced full-table Billy and WSP setlist existence scans with targeted lookups.
- Split Supabase credential expectations between pipeline (`SUPABASE_SERVICE_ROLE_KEY`) and website (`SUPABASE_ANON_KEY`).
- Updated GitHub Actions workflows to use `SUPABASE_SERVICE_ROLE_KEY`.
- Changed prediction publishing to store structured JSON payloads instead of JSON strings.
- Added tracked SQL for `get_table_schema` grant hardening in `supabase/migrations/20260320_restrict_get_table_schema.sql`.
- Added DB contract tests in `tests/test_db_operations.py`.
- Fixed the website performance route to enrich accuracy rows from band raw show tables instead of assuming `accuracy_per_show.venue_name` exists.

## Validation Status

- `uv run ruff check ...` on touched Python paths passed.
- `uv run pytest tests/test_db.py tests/test_db_operations.py tests/pipeline/test_band_collection_regressions.py tests/pipeline/test_run_optimized_pipeline.py` passed (`35 passed`).
- `npm run lint:web` passed.
- `npm run build:web` passed.
- Live Goose pipeline smoke passed with `--band goose --skip-accuracy`.
- Local website smoke passed for `/`, `/compare`, `/explorer`, and `/last-show` using `SUPABASE_ANON_KEY`.
- `/performance` initially failed against live schema (`accuracy_per_show.venue_name` missing), then passed after the website data-loader fix and final `npm run build:web`.
- Ruby YAML parse passed for `.github/workflows/daily-pipeline.yml` and `.github/workflows/test_secrets.yml`.

## Live Review Findings Captured In Code/Docs

- Live `notebook_accuracy` exists; `accuracy_notebook` does not.
- Live prediction rows were storing stringified JSON inside `jsonb`; the writer now sends structured JSON.
- The inspected website env contract was ambiguous enough to allow service-role misuse; the web app now requires `SUPABASE_ANON_KEY`.
- The website can read prediction, explorer, and last-show data with the anon key.
- `accuracy_per_show` does not store venue labels; the web app now joins those from the band raw shows table.

## Next Step

- Apply the tracked Supabase migration to production from an authenticated Supabase dashboard or CLI session, then do a live publish smoke test to confirm `get_table_schema` still works for pipeline contexts and the website continues to read through the non-secret key path.
- Apply the tracked Supabase migration to production from an authenticated Supabase dashboard or CLI session.
- Redeploy Vercel so the latest website fix for `/performance` is live.
- After deploy, smoke-check `/`, `/compare`, `/explorer`, `/last-show`, and `/performance` on the deployed site.

## Blocker

- Attempting to open the Supabase SQL editor from this session redirected to the Supabase sign-in page, so the migration could not be applied live from the current authenticated context.
