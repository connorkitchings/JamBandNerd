# Publish Dev To Main

## Goal

Publish the current `dev` branch state to `main` by committing all uncommitted
changes, pushing `dev`, and opening a PR to `main`.

## Scope

- Commit the existing dirty worktree on `dev`, including:
  - Deal Batch 2 analysis/report artifacts
  - Deal feature and normalization updates
  - bounded `prediction_songs` rebuild + daily-pipeline validation hardening
- Verify the changed areas with focused tests before publishing.

## Commands Run

- `uv run pytest tests/models/test_deal_model.py`
- `uv run pytest tests/pipeline/test_normalization_contract.py`
- `uv run pytest tests/pipeline/test_run_optimized_pipeline.py`
- `uv run pytest tests/test_operational_recovery_scripts.py`
- `uv run ruff check scripts/analyze_ablations.py scripts/rebuild_prediction_songs.py scripts/run_optimized_pipeline.py src/jambandnerd/models/deal/features.py src/jambandnerd/transformations/normalization.py tests/models/test_deal_model.py tests/pipeline/test_normalization_contract.py tests/pipeline/test_run_optimized_pipeline.py tests/test_operational_recovery_scripts.py`

## Validation

- Deal model tests passed.
- Normalization contract tests passed.
- Local optimized pipeline tests passed.
- Operational recovery script tests passed.
- Focused Ruff check passed for the modified Python files.

## Files In Scope

- `.github/workflows/daily-pipeline.yml`
- `docs/operations/github_actions.md`
- `scripts/README.md`
- `scripts/analyze_ablations.py`
- `scripts/rebuild_prediction_songs.py`
- `scripts/run_optimized_pipeline.py`
- `src/jambandnerd/models/deal/features.py`
- `src/jambandnerd/transformations/normalization.py`
- `tests/models/test_deal_model.py`
- `tests/pipeline/test_normalization_contract.py`
- `tests/pipeline/test_run_optimized_pipeline.py`
- `tests/test_operational_recovery_scripts.py`
- `docs/reports/model_baselines/ablations/batch2/`

## Next Step

Push `dev`, open the PR to `main`, and use the merged code as the baseline for
the production-facing prediction projection recovery.
