# Steady-State Documentation Review

**Date**: 2026-04-07
**Branch**: `docs/steady-state-review`

---

## Goal

Comprehensive repo review to verify the project is in a steady state after recent rapid development. Ensure all documentation is accurate, current, and consistent with the actual codebase.

## Constraints

- Do not introduce new features or behavioral changes
- Fix only documentation inaccuracies and pre-existing test failures
- Follow the end-session skill for proper closeout

## Commands Run

- `git status --short`
- `uv run ruff check src tests scripts`
- `uv run black --check src tests scripts`
- `uv run black src tests scripts`
- `uv run pytest` (3 times: baseline, post-docs, post-test-fix)
- `uv run pytest -q tests/pipeline/test_band_collection_regressions.py::test_wsp_process_uses_paginated_existing_setlist_reads`

## Files Changed

### Documentation fixes

- `pyproject.toml` — removed dangling `predict-goose` and `predict-phish` entry points
- `docs/reference/models/xgboost.md` → `docs/reference/models/deal.md` — renamed, fixed `--model xgboost` to `--model deal`, fixed table names, updated visibility docs
- `docs/reference/models/index.md` — fixed link from `xgboost.md` to `deal.md`, updated model registration instructions
- `docs/index.md` — fixed link from `xgboost.md` to `deal.md`
- `docs/user/pipeline_usage.md` — added 3 missing collection scripts (eggy, billy, um)
- `docs/operations/github_actions.md` — rewrote to cover all 9 workflows (was only 2)
- `scripts/README.md` — added ~13 missing scripts to appropriate categories
- `docs/contributor/developer_guide/architecture.md` — added Deal model, updated model platform section with table of 3 registered models
- `docs/overview/implementation_status.md` — updated with recent capabilities, fixed version, added all 9 workflows

### Test fix

- `tests/pipeline/test_band_collection_regressions.py` — added `insert`/`delete` methods to `_WSPQueryStub`, monkeypatched `classify_missing_recent_setlists` to fix pre-existing failure

### Auto-formatting (pre-existing drift from recent merges)

- 26 files reformatted by `black` (scripts, src, tests)

## Validation

- `uv run ruff check src tests scripts` — all checks passed
- `uv run black --check src tests scripts` — all files formatted
- `uv run pytest` — 183 passed, 6 skipped, 0 failures (was 182 passed, 1 failed, 6 skipped)

## Next Step

Merge `docs/steady-state-review` into `dev`, then PR to `main`.
