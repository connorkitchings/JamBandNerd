# Testing Guide

JamBandNerd has two main verification surfaces:

- Python tests under `tests/`
- Website smoke tests for `apps/web`

## Structure

- `tests/data_collection/` - collector- and source-specific tests
- `tests/models/` - model registry, readiness, and predictor behavior
- `tests/pipeline/` - consolidated script and orchestration coverage
- top-level `tests/test_*.py` - shared utilities, db, diagnostics, and support scripts
- `conftest.py` - shared fixtures and test environment setup

## Canonical Commands

```bash
# Canonical verification entrypoints
npm run verify:python
npm run verify:docs
npm run verify:web
npm run verify:all

# Final tracked-file drift check on a clean baseline
npm run verify:clean

# Explicit live checks that may touch production-like services
npm run test:python:live
npm run verify:python:live

# Component commands used by the verify scripts
uv run pytest --collect-only -q
uv run pytest -o addopts=-v -m live tests/pipeline/test_live_band_smoke.py
npm run test:web:smoke:list
```

## Notes

- Use `uv run ...` for Python commands.
- Run `npx playwright install --with-deps chromium` once after `npm install`
  before using the website smoke commands locally.
- `npm run verify:python` excludes tests marked `live` by default. Use the
  explicit live commands only when Supabase-writing smoke checks are intended.
- Website smoke coverage is the canonical frontend verification path and is also
  exercised in GitHub Actions.
