# Model Change

## When To Use

Use for prediction logic, feature usage, backtests, or metrics changes.

## Read Order

1. `.agent/CONTEXT.md`
2. `docs/reference/models/index.md`
3. `docs/reference/specifications/transformations.md`
4. `scripts/generate_predictions.py`
5. `scripts/run_backtest.py`

## Rules

- Preserve the `reference_date` cutoff.
- Keep changes band-agnostic unless the issue is truly source-specific.
- Pair logic changes with tests or a narrow reproducible validation path.

## Expected Validation

```bash
uv run pytest tests/test_models.py
uv run python scripts/run_backtest.py --band goose --model notebook --shows 10
```

## Common Mistakes

- Leaking future data into features
- Changing metrics without updating docs
- Forgetting to validate downstream scripts
