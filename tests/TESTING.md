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

# Component commands used by the verify scripts
uv run pytest --collect-only -q
npm run test:web:smoke:list
```

## Notes

- Use `uv run ...` for Python commands.
- Run `npx playwright install --with-deps chromium` once after `npm install`
  before using the website smoke commands locally.
- Live-band or environment-dependent tests are explicitly marked; most of the
  suite is designed to run without touching production services.
- Website smoke coverage is the canonical frontend verification path and is also
  exercised in GitHub Actions.
