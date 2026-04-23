# Daily Workflow Architecture Review And Final Stabilization

## Goal

- Align the daily workflow, band source-of-truth helpers, and active docs around one current architecture, then add drift checks so the same knowledge drift does not recur.

## Constraints

- Keep GitHub Actions YAML as the canonical daily orchestrator.
- Keep repo config as the authority for workflow-supported bands.
- Keep the unified Supabase tables as the active storage contract.
- Do not pull the unrelated untracked `.opencode` planning note into the commit.

## Commands Run

```bash
sed -n '1,240p' .agent/skills/start-session/SKILL.md
sed -n '1,220p' .agent/AGENTS.md
sed -n '1,220p' .agent/CONTEXT.md
sed -n '1,220p' .codex/QUICKSTART.md
sed -n '1,260p' pyproject.toml
sed -n '1,260p' README.md
sed -n '1,260p' docs/user/pipeline_usage.md
sed -n '1,280p' docs/contributor/developer_guide/architecture.md
git status --short --branch
sed -n '1,280p' docs/reference/specifications/data_strategy.md
sed -n '1,260p' docs/operations/github_actions.md
sed -n '1,260p' .github/workflows/daily-pipeline.yml
sed -n '1,280p' scripts/run_optimized_pipeline.py
sed -n '1,260p' scripts/generate_predictions.py
sed -n '1,280p' scripts/run_backtest.py
sed -n '1,280p' scripts/audit_supabase_tables.py
sed -n '1,240p' src/jambandnerd/models/registry.py
sed -n '1,260p' src/jambandnerd/models/metadata.py
sed -n '1,260p' docs/reference/specifications/database.md
sed -n '1,260p' docs/reference/specifications/predictions_schema.md
sed -n '1,260p' docs/reference/schemas/unified_tables.md
sed -n '1,260p' docs/reference/specifications/cli.md
sed -n '1,260p' docs/reference/specifications/goose_pipeline.md
sed -n '1,260p' docs/contributor/model_readiness.md
sed -n '1,220p' scripts/get_all_bands.py
sed -n '1,220p' src/jambandnerd/db/operations.py
uv run pytest tests/test_band_sources_of_truth.py tests/test_daily_workflow_contract.py tests/pipeline/test_run_optimized_pipeline.py tests/pipeline/test_run_backtest.py tests/test_validate_prediction_tables.py tests/test_validate_accuracy_tables.py tests/test_check_supported_model_freshness.py tests/test_audit_supabase_tables.py tests/test_collection_preflight.py -q
npm run verify:python
npm run verify:docs
uv run black tests/test_daily_workflow_contract.py scripts/audit_shared_model_inputs.py
npm run verify:python
npm run verify:docs
```

## Files And Artifacts

- `src/jambandnerd/config/bands.py` — split repo-authoritative workflow band helpers from runtime registry metadata helpers
- `scripts/get_all_bands.py` plus affected pipeline/diagnostic scripts — rewired workflow/CLI band selection to use repo-supported bands
- `.github/workflows/daily-pipeline.yml` — clarified orchestration ownership and per-show accuracy wording
- `README.md`, `docs/user/pipeline_usage.md`, `docs/contributor/developer_guide/architecture.md`, `docs/operations/github_actions.md`, `docs/reference/specifications/{data_strategy,database,cli}.md`, `scripts/README.md`, and related docs — corrected active contract wording
- `docs/reports/2026-04-22_daily_workflow_architecture_review.md` — explicit architecture review artifact
- `tests/test_band_sources_of_truth.py` — new guard for repo-vs-runtime band helper semantics
- `tests/test_daily_workflow_contract.py` — new guard for workflow/doc drift
- `.agent/PLAYBOOK.md` — added durable lesson about splitting workflow truth from runtime metadata

## Validation

- Targeted workflow/data-contract test slice passed: `76 passed`
- `npm run verify:python` passed after formatting the two files Black flagged
- `npm run verify:docs` passed

## Next Step

- Merge `codex/daily-workflow-final-stabilization` into `dev`, then open the `dev -> main` PR and monitor the next scheduled daily pipeline run for production confirmation.
