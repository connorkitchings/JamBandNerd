# Session Log: 2026-03-27

## Summary

Completed the final website hardening pass, added balanced `main`-branch governance artifacts, and rewrote the Deal model into an explainable logistic ranker with dedicated diagnostics and tests.

## Website

- Replaced remote Google font usage with local/system stacks so `npm run build:web` no longer depends on network font fetches.
- Added cookie-backed admin session auth for the internal setlist route.
- Introduced domain ownership entrypoints under `apps/web/src/lib/data/` and documented the data-layer split.
- Updated smoke tests to reflect the current mobile shell and fallback states.

## Governance

- Added `Repo Quality` GitHub Actions workflow.
- Removed path filters from `Website Quality` so required checks can be enforced on every PR.
- Added `.github/CODEOWNERS`, a pull request template, and `docs/operations/main_branch_elevation.md`.

## Deal Model

- Replaced the XGBoost-based Deal prototype with a logistic ranking model trained on true per-show candidate rows.
- Added JSON artifact persistence with model metadata, coefficients, calibration summary, and probability distribution stats.
- Added `scripts/evaluate_deal_model.py` for Deal diagnostics and comparison reporting.
- Added `tests/models/test_deal_model.py` for leakage, training-frame, probability-spread, and roundtrip coverage.

## Verification

- `npm run lint:web`
- `npm run build:web`
- `npm run test:web:smoke`
- `uv run ruff check src tests scripts`
- `uv run pytest tests/models tests/pipeline/test_run_backtest.py tests/pipeline/test_run_optimized_pipeline.py`

## Follow-up

- The repository now contains the ruleset/runbook artifacts for `main`, but the actual GitHub branch ruleset still needs to be applied in the GitHub UI.
