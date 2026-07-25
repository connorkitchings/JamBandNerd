# Weekly Workflow Failure Remediation

## Goal

- Resolve the recurring dependency-audit failure and stop expected WSP upstream-publication lag from failing the daily pipeline over immutable accuracy freshness.

## Constraints

- Keep live prediction freshness as a 48-hour hard failure.
- Limit the automatic accuracy-warning path to WSP `degraded_upstream_lag`; collector regressions, true upstream failures, and normal runs remain strict.
- Do not change database schema, website APIs, or prediction-model behavior.

## Commands Run

```bash
uv lock --upgrade-package soupsieve
uv run pytest -q tests/test_daily_workflow_contract.py tests/test_check_supported_model_freshness.py tests/test_audit_supabase_tables.py
uv run black --check tests/test_daily_workflow_contract.py tests/test_check_supported_model_freshness.py tests/test_audit_supabase_tables.py
uv run ruff check tests/test_daily_workflow_contract.py tests/test_check_supported_model_freshness.py tests/test_audit_supabase_tables.py
uv export --format requirements-txt --locked --no-hashes --no-emit-project --output-file /tmp/jbn-soupsieve-audit-requirements.txt
uv run --with pip-audit python -m pip_audit -r /tmp/jbn-soupsieve-audit-requirements.txt --cache-dir /tmp/jbn-pip-audit-cache --no-deps --disable-pip
npm run verify:python
npm run verify:docs
```

## Files And Artifacts

- `.github/workflows/daily-pipeline.yml` scopes automatic `--skip-accuracy` to manual dispatches and WSP `degraded_upstream_lag` outputs for both freshness audits.
- `uv.lock` upgrades transitive `soupsieve` from 2.7 to 2.9.1.
- Added workflow and freshness/audit regression coverage; updated GitHub Actions and implementation-status documentation.
- Added a reusable degraded-accuracy freshness lesson to `.agent/PLAYBOOK.md`.

## Validation

- Focused workflow and audit tests: 24 passed.
- Locked dependency audit: no known vulnerabilities found.
- `npm run verify:python`: passed (611 tests; 10 live tests deselected).
- `npm run verify:docs`: passed.

## Next Step

- Commit the remediation and confirm the next scheduled Dependency Audit and WSP daily run stay green.
