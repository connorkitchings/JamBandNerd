# 2026-03-23 Session Log 01

## Goal

Harden daily pipeline monitoring by replacing the workflow's inline summary logic with a shared script that uses the same completed-show freshness rules as the standalone data checks.

## Constraints

- Preserve the existing workflow behavior outside the summary-generation path.
- Exclude today and future scheduled shows from freshness warnings.
- Use batched/paginated Supabase reads for summary checks instead of one-shot queries that can drift or truncate.

## Commands Run

```bash
git checkout -b chore-pipeline-summary-hardening
uv run black scripts/common.py scripts/verify_data_freshness.py scripts/generate_pipeline_summary.py tests/test_data_diagnostics_scripts.py tests/test_generate_pipeline_summary.py
uv run pytest tests/test_generate_pipeline_summary.py tests/test_data_diagnostics_scripts.py -v
uv run ruff check scripts/common.py scripts/verify_data_freshness.py scripts/generate_pipeline_summary.py tests/test_data_diagnostics_scripts.py tests/test_generate_pipeline_summary.py
```

## Files And Artifacts

- `.github/workflows/daily-pipeline.yml`
- `docs/operations/github_actions.md`
- `scripts/README.md`
- `scripts/common.py`
- `scripts/verify_data_freshness.py`
- `scripts/generate_pipeline_summary.py`
- `tests/test_data_diagnostics_scripts.py`
- `tests/test_generate_pipeline_summary.py`
- `session_logs/2026-03-23/01_pipeline_summary_hardening.md`

## Validation

- Focused pytest coverage passed for the new summary script and completed-show window helpers.
- Ruff passed on all touched Python files.
- Black applied cleanly to the touched Python files.

## Next Step

Watch the next `daily-pipeline` GitHub Actions run and confirm the summary output matches the standalone freshness checks, especially for bands with no recent completed shows or missing setlists.
