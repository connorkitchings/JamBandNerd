# Deal Readiness Report And Cache Resume

## Summary

Implemented a decision-oriented readiness layer on top of the cached model
comparison workflow, then seeded the first resumable all-band Deal readiness
run.

## Repo Changes

- Added `replacement_readiness` and `candidate_weak_shows` output to
  `scripts/compare_models.py`.
- Added readiness/weak-show helper logic to
  `src/jambandnerd/models/comparison.py`.
- Extended comparison regression coverage in
  `tests/pipeline/test_compare_models.py`.
- Updated experimental model workflow docs in:
  - `docs/contributor/model_development.md`
  - `docs/reference/models/deal.md`
  - `docs/reference/specifications/cli.md`
  - `scripts/README.md`
  - `docs/reports/model_baselines/README.md`

## Readiness Output

Each comparison window now emits:

- `replacement_readiness`
  - CK+ gate result
  - cross-band deltas vs the readiness baseline
  - weak bands ranked by recall deltas
  - failure-driver classification: `ranking_accuracy`,
    `probability_quality`, `both`, or `healthy`
  - internal canary/shadow safety checks
- `candidate_weak_shows`
  - per-band worst historically scored shows versus the readiness baseline

## Verification

Passed:

```bash
uv run ruff check src/jambandnerd/models/comparison.py scripts/compare_models.py tests/pipeline/test_compare_models.py
uv run pytest tests/pipeline/test_compare_models.py
uv run pytest tests/pipeline/test_run_backtest.py tests/models/test_model_test_cache.py
```

## Cached Readiness Run

Started the canonical Deal readiness command:

```bash
uv run python scripts/compare_models.py --candidate-model deal --band all --fresh-training --include-candidate-diagnostics --output docs/reports/model_baselines/2026-04-09_deal_readiness_all_last50.json
```

State captured during this session:

- cache dir:
  `docs/reports/model_baselines/cache/deal__shared_core_v1__813a0a9e355985dd`
- report path:
  `docs/reports/model_baselines/2026-04-09_deal_readiness_all_last50.json`
- resumable report state after `eggy` completed:
  - `report_status=partial`
  - `completed_bands=["eggy"]`
  - `cache_summary.record_count=150`

The same command can be rerun to resume from the partial artifact and existing
cache rows rather than restart from scratch.
