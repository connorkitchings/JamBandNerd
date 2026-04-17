# Deal Window Contract And Playwright Cache

**Goal:** Make Deal daily backtests operationally cheaper by formalizing a `10`-show readiness window, while adding Playwright browser caching to the workflows that reinstall browsers every run.
**Constraints:** Keep Notebook at `50`, preserve the existing website-facing audit flow, avoid one-off CI hacks that diverge from registry metadata, and keep workflow behavior aligned with docs.
**Validation Status:** Targeted Python validation and docs verification passed locally in this session.

## Actions Taken
- Changed Deal model metadata so its registry `readiness_windows` is now `10` instead of `50`.
- Updated the daily pipeline workflow to run Notebook backtests with `--shows 50` and Deal with `--shows 10`.
- Added Playwright browser caching to the daily pipeline, Fantasy Goose, Website Quality, and Hosted Website Smoke workflows while keeping OS dependency installation separate.
- Updated `validate_accuracy_tables.py` so replay-lineage validation derives its required window from model registry metadata unless a CLI override is supplied.
- Updated model registry/readiness tests and refreshed docs/runbooks to describe model-specific replay windows instead of a universal `50`-show assumption.

## Key Outcome
- The repo now treats Deal’s smaller replay/readiness window as an explicit contract rather than an undocumented CI shortcut. Workflow commands, validation logic, and docs all point at the same rule.

## Commands Run
- `uv run pytest tests/test_validate_accuracy_tables.py tests/models/test_model_registry.py tests/models/test_model_readiness.py tests/test_check_supported_model_freshness.py tests/test_audit_supabase_tables.py`
- `npm run verify:docs`
- `git diff --check`

## Files Changed Or Artifacts Produced
- Workflow updates: `.github/workflows/daily-pipeline.yml`, `.github/workflows/fantasy-goose.yml`, `.github/workflows/web-quality.yml`, `.github/workflows/hosted-web-smoke.yml`
- Runtime contract updates: `src/jambandnerd/models/metadata.py`, `scripts/validate_accuracy_tables.py`
- Tests: `tests/test_validate_accuracy_tables.py`, `tests/models/test_model_registry.py`, `tests/models/test_model_readiness.py`
- Docs and operating guidance: `docs/operations/github_actions.md`, `docs/contributor/model_readiness.md`, `docs/reference/specifications/data_strategy.md`, `.agent/PLAYBOOK.md`
- Session artifact: `session_logs/2026-04-17/05_deal_window_contract_and_playwright_cache.md`

## Next Step
- Push the branch, open a PR to `main`, then verify the next daily workflow dispatch shows Deal finishing inside the reduced window and Playwright cache hits on rerun.
