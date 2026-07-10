# Repo Review Stabilization

## Goal

Implement the repo review stabilization plan: make default Python verification safe, clarify band scopes, extract shared model helpers, clean web data access, and refresh active documentation.

## Constraints

- Preserve public website routes and database schema.
- Keep active model version strings and prediction behavior stable.
- Eggy remains collectable but outside default single-model daily publishing until intentionally promoted.
- Default verification must not run Supabase-writing live smoke tests.

## Commands Run

- `uv run pytest -q tests/test_band_sources_of_truth.py tests/test_daily_workflow_contract.py tests/models/test_shared_matrix_features.py`
- `uv run pytest --collect-only -q tests/pipeline/test_live_band_smoke.py`
- `uv run pytest -o addopts=-v -m live tests/pipeline/test_live_band_smoke.py --collect-only -q`
- `uv run ruff check ...`
- `uv run black ...`
- `npm run verify:python`
- `npm run verify:docs`
- `npm run verify:web`
- `git diff --check`

## Files Changed Or Artifacts Produced

- Added explicit collectable, active-model, and daily-pipeline band scopes in `src/jambandnerd/config/bands.py`.
- Updated `scripts/get_all_bands.py`, `scripts/run_optimized_pipeline.py`, and `.github/workflows/daily-pipeline.yml` to read daily publishing bands from config.
- Changed pytest defaults and npm scripts so live tests are opt-in, and added a timeout to live band pipeline subprocess tests.
- Moved shared rank/run/gap helpers into `jambandnerd.models.shared` and updated Phish, Billy, UM, and WSP predictors to use them.
- Added shared-helper and band-scope contract tests.
- Added `apps/web/src/lib/data/model-version.ts`, narrowed public Supabase projections, and removed service-role fallback from public accuracy reads.
- Updated active docs in `.agent/CONTEXT.md`, `README.md`, `docs/user/pipeline_usage.md`, `docs/operations/github_actions.md`, schema docs, and `tests/TESTING.md`.
- Added `web/README.md` documenting the top-level `web/` directory as a legacy placeholder.
- Added this session log and a reusable playbook lesson.

## Validation Status

- `npm run verify:python` passed with `608 passed, 10 deselected`.
- `npm run verify:docs` passed.
- `npm run verify:web` passed.
- Explicit live smoke collection passed with 10 collected tests; live tests were not executed.
- `git diff --check` passed.
- `npm run verify:clean` was not run before commit because it is intended for a clean worktree and would fail while implementation changes were intentionally uncommitted.

## Next Step

Open a PR from `codex/repo-review-stabilization` and use CI plus optional explicit live smoke checks to validate the branch before merge.
