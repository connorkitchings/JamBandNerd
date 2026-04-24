# Workflow Supabase Efficiency Cleanup

## Goal

- Align the local optimized pipeline helper with the production daily workflow and make Supabase audit output clearer when immutable accuracy timestamps are intentionally tolerated.

## Constraints

- Keep `.github/workflows/daily-pipeline.yml` as the canonical production orchestrator.
- Preserve prediction freshness as a hard requirement.
- Treat stale accuracy timestamps as acceptable only when incremental backtest reports all shows already scored.
- Do not remove ignored local artifacts automatically.

## Commands Run

```bash
git status --short --branch
uv run pytest tests/pipeline/test_run_optimized_pipeline.py tests/test_audit_supabase_tables.py tests/test_check_supported_model_freshness.py -q
uv run black scripts/run_optimized_pipeline.py scripts/audit_supabase_tables.py tests/pipeline/test_run_optimized_pipeline.py tests/test_audit_supabase_tables.py
npm run verify:python
npm run verify:docs
npm run verify:web
uv run python scripts/audit_supabase_tables.py --skip-accuracy
gh run list --workflow=daily-pipeline.yml --limit 3 --json databaseId,status,conclusion,createdAt,event,headBranch
npm run verify:clean
```

## Files And Artifacts

- `scripts/run_optimized_pipeline.py` — local helper now batches default plus last-completed predictions, requires prediction output, mirrors all-scored accuracy freshness handling, runs the Supabase audit, and skips prediction/backtest work after verify-only preflight unless `--force` is passed.
- `scripts/audit_supabase_tables.py` — `--skip-accuracy` output now labels stale accuracy as expected immutable freshness drift for already-scored windows.
- `tests/pipeline/test_run_optimized_pipeline.py` and `tests/test_audit_supabase_tables.py` — added coverage for batched local orchestration, verify-only/force behavior, all-scored freshness skipping, local audit wiring, and audit output wording.
- `docs/user/pipeline_usage.md` and `scripts/README.md` — documented `--force` and ignored local artifact cleanup guidance.
- `.agent/PLAYBOOK.md` — added a durable pattern about keeping local orchestration helpers aligned with workflow gates.

## Validation

- Targeted tests passed: `46 passed`.
- `npm run verify:python` passed: `340 passed, 6 skipped`.
- `npm run verify:docs` passed.
- `npm run verify:web` passed outside the sandbox; the sandboxed attempt failed with a Turbopack port-bind permission panic.
- Live Supabase audit with `--skip-accuracy` exited 0 with warning state and no blockers.
- Latest daily pipeline check showed the most recent scheduled run on `main` succeeded: run `24854627359`, created `2026-04-23T19:28:53Z`.
- `npm run verify:clean` failed because this session intentionally leaves tracked changes to be reviewed/committed.

## Next Step

- Review and commit the workflow/audit/docs changes, then push through the usual PR path.
