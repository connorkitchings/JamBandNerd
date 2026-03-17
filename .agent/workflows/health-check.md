# Health Check Workflow

Run these checks before shipping non-trivial changes.

## Full Validation

```bash
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest
```

## Narrow Validation During Iteration

Use narrower commands when appropriate:

```bash
uv run pytest tests/test_models.py
uv run pytest tests/web/test_predictions.py
uv run python scripts/verify_data_freshness.py --band goose
uv run python scripts/validate_prediction_tables.py --band goose
```

## Notes

- Use `README.md` and `docs/user/pipeline_usage.md` for canonical run commands.
- If a command is skipped, record that explicitly in the session log or summary.
