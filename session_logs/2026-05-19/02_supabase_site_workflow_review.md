# Supabase Site + Daily Workflow Review

## Goal
- Review the website Supabase read paths, daily workflow write/validation path, and prediction/history table contracts before continuing the production promotion.

## Findings
- Public website pages read through the server Supabase anon client and use the website-facing `setlist_*` tables for predictions, replay, and performance surfaces.
- Latest production `main` daily workflow run `26055758296` completed successfully for `goose`, `phish`, `wsp`, `billy`, and `um`.
- The downloaded per-band artifacts reported `workflow_state=success`, `prediction_action=generated`, `freshness_state=fresh`, `supabase_audit_state=ok`, and zero audit blockers/warnings for every active band.
- Production artifacts still reflect the model versions currently on `main`; Billy and UM artifacts are not yet proving the V12 `dev` metadata.

## Changes Made
- Tightened `.github/workflows/daily-pipeline.yml` so live prediction generation uses `--require-output`.
- Updated the workflow contract test to enforce `--require-output`.
- Updated `apps/web/src/lib/data/predictions.ts` so date-based prediction/history lookup filters by the latest active model version when available, avoiding stale historical rows from older model versions.

## Validation
- `uv run pytest -q tests/test_daily_workflow_contract.py tests/test_validate_prediction_tables.py tests/test_validate_accuracy_tables.py tests/test_audit_supabase_tables.py`
- `npm run lint --workspace apps/web`
- `npm run build --workspace apps/web`

## Notes
- Local Supabase credentials were not present in the shell, so live local table validation was not run.
- GitHub artifact downloads were used as the credentialed production evidence source.
