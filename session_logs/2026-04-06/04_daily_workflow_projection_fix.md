# Daily Workflow Projection Validation Fix

**Date**: 2026-04-06
**Branch**: `dev`

---

## Goal

Fix the scheduled GitHub `Daily Data Pipeline` failures caused by `prediction_songs` projection validation mismatches.

## Constraints

- Do not touch unrelated dirty changes in `apps/web`.
- Keep the fix scoped to projection cleanup and validation behavior.
- Preserve the current workflow structure unless the code fix proves insufficient.

## Commands Run

- `sed -n '1,220p' .agent/AGENTS.md`
- `sed -n '1,220p' .agent/skills/start-session/SKILL.md`
- `sed -n '1,220p' .agent/CONTEXT.md`
- `sed -n '1,220p' pyproject.toml`
- `sed -n '1,220p' README.md`
- `sed -n '1,260p' docs/user/pipeline_usage.md`
- `sed -n '1,260p' docs/contributor/developer_guide/architecture.md`
- `sed -n '1,240p' docs/operations/github_actions.md`
- `sed -n '1,240p' .agent/skills/pipeline-debug/SKILL.md`
- `git status --short`
- `gh run list --limit 20 --json databaseId,displayTitle,event,headBranch,name,number,status,conclusion,workflowName,createdAt,updatedAt,url`
- `gh run view 24047053702 --json jobs,name,displayTitle,conclusion,createdAt,updatedAt,url,workflowName`
- `gh run view 24047053702 --log-failed`
- `gh run list --workflow "Daily Data Pipeline" --limit 10 --json databaseId,conclusion,createdAt,url`
- `gh run view 23866641249 --json jobs,conclusion,createdAt,url`
- `gh run view 23866641249 --log-failed`
- `uv run pytest -q tests/test_validate_prediction_tables.py tests/test_db_operations.py`
- `uv run ruff check src/jambandnerd/db/operations.py scripts/validate_prediction_tables.py tests/test_validate_prediction_tables.py tests/test_db_operations.py`

## Files Changed

- `src/jambandnerd/db/operations.py`
- `scripts/validate_prediction_tables.py`
- `tests/test_validate_prediction_tables.py`
- `tests/test_db_operations.py`

## Validation

- Confirmed the latest scheduled failure (`Daily Data Pipeline` run `#321`) was not a collector regression.
- Traced the break to projection retention and validation logic introduced by the same-day `prediction_songs` cleanup work.
- Added targeted tests covering stale future-dated projections and `predicted_at`-based cleanup semantics.
- Passed targeted verification:
  - `uv run pytest -q tests/test_validate_prediction_tables.py tests/test_db_operations.py`
  - `uv run ruff check src/jambandnerd/db/operations.py scripts/validate_prediction_tables.py tests/test_validate_prediction_tables.py tests/test_db_operations.py`

## Next Step

Re-run the `Daily Data Pipeline` workflow on `main` to confirm prediction validation now passes for Goose, Eggy, UM, and Phish.
