# Prediction Validator Fix

## Goal

- Make prediction freshness validation use the most recently written prediction row so cross-band verification and CI do not report false stale failures.

## Constraints

- Keep the existing CLI and failure semantics for `scripts/validate_prediction_tables.py`.
- Do not require workflow changes in GitHub Actions or `run_optimized_pipeline.py`.

## Commands Run

```bash
uv run pytest tests/test_validate_prediction_tables.py -q
uv run python -m py_compile scripts/validate_prediction_tables.py
uv run python scripts/validate_prediction_tables.py --band goose --max-age-hours 2
uv run python scripts/validate_prediction_tables.py --band um --max-age-hours 2
uv run python scripts/validate_prediction_tables.py --band wsp --max-age-hours 2
```

## Files And Artifacts

- `scripts/validate_prediction_tables.py`: fetch the latest row by `predicted_at`, with `reference_date` as a deterministic tiebreaker.
- `tests/test_validate_prediction_tables.py`: regression coverage for false-stale ordering, invalid JSON, and missing `predicted_at`.
- `scripts/README.md`: documents that freshness validation uses the latest written row.
- `docs/operations/github_actions.md`: clarifies the CI semantics of prediction freshness validation.

## Validation

- New tests passed: `3 passed`.
- Goose now validates cleanly against fresh writes instead of being masked by farther-future historical rows.
- UM now validates cleanly for the same reason.
- WSP still validates cleanly after the earlier ingestion repair.

## Next Step

- Re-run the compact cross-band verification summary and then focus only on the remaining real review items: `eggy`, `um`, and `billy` ingestion/data-quality gaps.
