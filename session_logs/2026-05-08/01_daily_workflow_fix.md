# Daily Workflow Fix — May 8, 2026

## Problem
Daily pipeline workflow failed for all bands (phish, goose, eggy, wsp) starting May 6th, 2026 at the "Validate Prediction Tables" step.

## Root Cause
Commit e707884 (May 6th) centralized `parse_timestamp` into `scripts.common` but three scripts that import from it were missing the `sys.path` setup needed to find the `scripts` package when run directly:

1. `scripts/validate_prediction_tables.py`
2. `scripts/validate_accuracy_tables.py`
3. `scripts/check_supported_model_freshness.py`

This caused `ModuleNotFoundError: No module named 'scripts'` when the workflow ran these scripts via `uv run python scripts/<script>.py`.

## Fix
Added standard project root path setup to all three scripts:

```python
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)
```

## PRs
- PR #119: Added diagnostic logging to validation script (merged)
- PR #120: Fixed sys.path setup for all affected scripts (merged)

## Verification
Manual workflow run on dev branch succeeded for Goose band:
- Run: https://github.com/connorkitchings/JamBandNerd/actions/runs/25558417415
- Status: All jobs passed (Setup, Daily Pipeline - goose, Pipeline Summary)

## Playbook Lesson
When centralizing utilities into `scripts.common`, ensure all importing scripts have the `sys.path` setup pattern. Other scripts like `generate_live_predictions.py` already had this pattern — use it as a reference.

## Commands Run
```bash
gh run list --workflow=daily-pipeline.yml --limit 5
gh run view 25517576880 --json jobs
gh run download 25517576880 --dir /tmp/run_logs
npm run verify:python
gh workflow run daily-pipeline.yml --ref dev -f band=goose
```

## Files Changed
- `scripts/validate_prediction_tables.py` — diagnostic logging + sys.path fix
- `scripts/validate_accuracy_tables.py` — sys.path fix
- `scripts/check_supported_model_freshness.py` — sys.path fix
- `tests/test_validate_prediction_tables.py` — updated assertions for new message format
- `.agent/PLAYBOOK.md` — added lesson on sys.path pattern for scripts.common imports

## Validation Status
- `npm run verify:python`: passed (404 tests, 1 pre-existing unrelated failure in billy collection)
- Manual workflow run on dev: all jobs succeeded for Goose band
- Next scheduled daily run on main expected to succeed

## Next Step
Monitor the next scheduled daily run (19:00 UTC) to confirm all 6 bands pass; if any fail, check the new diagnostic output for the specific failure mode.
