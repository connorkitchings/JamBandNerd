# 2026-03-19 Session Log 09

## Goal

Complete the Streamlit retirement that was planned throughout today's sessions. Retire the legacy codebase, remove the dependency, clean all references, and ship a website-only product surface.

## Constraints

- Keep `apps/web` independent — no shared Streamlit code.
- Preserve `validate_environment()` in `connection.py` since tests import it.
- Delete `tests/web/` since those tests tested the Streamlit app, not the website.
- All quality gates must pass before committing.

## Commands Run

```bash
# Deletions
rm -rf src/jambandnerd/web/
rm -f src/jambandnerd/config/web.py
rm -rf .streamlit/
rm -f docs/operations/streamlit_deploy.md

# Removal from pyproject.toml
# (edit) removed "streamlit" from dependencies

# Quality gates
uv run black src tests scripts
uv run ruff check src tests scripts --fix
uv run pytest tests/test_db.py -v
npm run lint:web
npm run build:web

# Commit
git add -A && git commit -m "Retire Streamlit app..."
git push origin streamlined
```

## Files Changed Or Artifacts Produced

### Deleted
- `src/jambandnerd/web/` (entire Streamlit app: app.py, data.py, theme.py, style.css, components/, modules/)
- `src/jambandnerd/config/web.py` (STREAMLIT_CACHE_TTL constants)
- `.streamlit/config.toml`
- `docs/operations/streamlit_deploy.md`
- `tests/web/` (all Streamlit-specific tests: conftest.py, test_data.py, test_predictions.py, test_last_show.py, test_compare.py, test_performance.py, test_data_quality.py)

### Modified
- `pyproject.toml` — removed `streamlit` from dependencies
- `src/jambandnerd/db/connection.py` — removed `st.secrets` try/except; rewrote with env-only path; restored `validate_environment()`
- `src/jambandnerd/config/__init__.py` — removed `STREAMLIT_CACHE_TTL`, `STREAMLIT_CACHE_TTL_LONG`, `EXCLUDED_SHOW_DATES`, `MAX_ACCURACY_SHOWS` re-exports
- `.agent/AGENTS.md` — removed boot-order reference to `streamlit_deploy.md`
- `.codex/QUICKSTART.md` — replaced `uv run streamlit run...` with `npm install && npm run dev:web`
- `docs/ROADMAP.md` — rewrote intro, updated phases 3-4 to reflect completed retirement
- `docs/overview/implementation_status.md` — removed Legacy Presentation Surface section; updated notes
- `docs/overview/project/prd.md` — updated parity goal language
- `docs/contributor/onboarding.md` — removed web/ directory reference
- `docs/contributor/developer_guide/extending_the_platform.md` — removed "update legacy Streamlit" wording (2 places)
- `docs/user/configuration.md` — updated band/model config guidance (2 places)
- `docs/index.md` — removed legacy Streamlit link
- `docs/operations/mobile_verification.md` — removed Streamlit fallback reference
- `tests/test_db.py` — updated import and error message assertions for rewritten `connection.py`

### Post-Doc-Check Fixes (from session 01)
- `docs/operations/website_delivery.md` — added `/about` and `/predictions` to post-deploy checklist
- `docs/troubleshooting/data_ingestion_and_streamlit_issues.md` — retitled; updated opening paragraph

## Validation Status

- `uv run black src tests scripts`: 18 files reformatted, 101 left unchanged ✅
- `uv run ruff check src tests scripts`: All checks passed ✅
- `uv run pytest tests/test_db.py -v`: 6/6 passed ✅
- `npm run lint:web`: passed ✅
- `npm run build:web`: 9 routes built successfully ✅
- `git status --short`: clean staged state ✅
- `git push origin streamlined`: pushed ✅
- No `import st`, `import streamlit`, or `from jambandnerd.web` remaining in `src/` ✅
- `apps/web/` has no imports from `src/jambandnerd/web/` ✅

## Next Step

Merge PR #6 (`streamlined` → `main`), then connect the repo to Vercel with `apps/web` as root directory and `SUPABASE_URL` + `SUPABASE_KEY` env vars.
