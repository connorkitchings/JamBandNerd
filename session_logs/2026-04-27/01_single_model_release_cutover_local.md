# Single-Model Release Cutover Local Closeout

## Goal

Implement the full pre-Phase-B single-model cutover plan as far as the local
worktree can support: active docs cleanup, web test standardization, removed
route smoke coverage, version bump, Fantasy Goose `setlist_*` cutover, and local
verification.

## Constraints

- No local `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY` was present, so live
  Supabase migration confirmation, data population, and populated-state audits
  could not run from this shell.
- Hosted Vercel preview/production smoke and main promotion remain remote
  release gates.
- Eggy remains excluded from the Phase A active single-model rollout.

## Commands Run

- `node --test apps/web/tests/unit/*.test.ts`
- `uv run pytest tests/test_db_operations.py tests/test_fantasy_goose.py -q`
- `uv run python scripts/check_version_sync.py`
- `uv run black src/jambandnerd/db/operations.py scripts/play_fantasy_goose.py tests/test_db_operations.py`
- `uv run ruff check src/jambandnerd/db/__init__.py src/jambandnerd/db/operations.py src/jambandnerd/integrations/fantasy_goose.py scripts/play_fantasy_goose.py tests/test_db_operations.py --fix`
- `uv run black --check src tests scripts`
- `uv run ruff check src tests scripts`
- `npm run build:web`
- `npm run verify:docs` (rerun outside sandbox after uv cache permission failure)
- `npm run verify:python` (rerun outside sandbox after uv cache permission failure)
- `npm run verify:web` (rerun outside sandbox after local port/Turbopack sandbox failure)

## Files Changed Or Artifacts Produced

- Bumped release version to `0.3.0` across Python package, website package,
  website footer, lockfile, and implementation status docs.
- Added `npm run test:web:unit` and included it in `npm run verify:web`.
- Moved song-board pure helpers to alias-free
  `apps/web/src/lib/song-board-core.ts` so Node's test runner can execute the
  unit tests without Next path aliases.
- Added smoke coverage for `/contact` and explicit 404 checks for removed
  multi-model routes.
- Updated active docs/runbooks away from current `/compare`, `/replay`,
  `/explorer`, model picker, and model-slug product guidance; retained legacy
  comparison/recovery references as off-primary-path baseline or rollback
  tooling.
- Switched Fantasy Goose prediction lookup from legacy Goose Notebook projection
  to the single-model `setlist_predictions` + `setlist_prediction_songs`
  contract.
- Added `fetch_setlist_prediction_songs_for_date()` and a focused DB operation
  regression test.
- Added reusable playbook guidance for the single-model cutover and current
  selector pattern.

## Validation

- Web unit tests: 16 passed.
- Focused Python tests: 26 passed.
- `uv run black --check src tests scripts`: passed.
- `uv run ruff check src tests scripts`: passed.
- `npm run build:web`: passed.
- `npm run verify:docs`: passed.
- `npm run verify:python`: 342 passed, 6 skipped.
- `npm run verify:web`: 10 passed, 10 skipped after build/lint/unit checks.

Not run:
- Supabase populated-state checks and data population, blocked by missing local
  Supabase service-role environment variables.
- `npm run verify:clean`, because the implementation changes are intentionally
  still uncommitted in the working tree.
- Hosted Website Smoke against Vercel preview/production, because no deployed
  URL/main promotion was performed from this local session.

## Next Step

Load Supabase service-role credentials or run the GitHub workflows, populate the
active Phase A bands into `setlist_*`, run populated-state audits, then verify a
Vercel preview before merging to `main`.
