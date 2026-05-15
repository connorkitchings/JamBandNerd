# Billy Baseline Acceptance — V3

## Goal

Accept `BillyFastPredictorV3` as the current Billy baseline before starting the
larger architecture experiment.

## Constraints

- Keep historical experiment imports and artifacts stable.
- Do not promote V6 after the early-stopping backtest missed the gate.

## Commands Run

```bash
uv run pytest tests/models/test_billy_model.py tests/models/test_model_registry.py -q
uv run ruff check src/jambandnerd/models/billy/fast_predictor.py src/jambandnerd/models/billy/__init__.py src/jambandnerd/models/registry.py src/jambandnerd/models/metadata.py tests/models/test_billy_model.py tests/models/test_model_registry.py
uv run black src/jambandnerd/models/billy/fast_predictor.py src/jambandnerd/models/billy/__init__.py src/jambandnerd/models/registry.py src/jambandnerd/models/metadata.py tests/models/test_billy_model.py tests/models/test_model_registry.py
npm run verify:docs
```

## Files And Artifacts

- `src/jambandnerd/models/billy/fast_predictor.py`: added
  `BillyFastBaselinePredictor = BillyFastPredictorV3`.
- `src/jambandnerd/models/registry.py`: registry now points Billy at the stable
  baseline alias.
- `src/jambandnerd/models/metadata.py`: Billy `model_version` is now
  `billy_fast_gbm_v3`.
- `docs/contributor/developer_guide/architecture.md` and `.agent/PLAYBOOK.md`:
  documented V3 as the accepted baseline.

## Validation

- Billy model and registry tests passed.
- Ruff clean on touched Python files.
- Docs built cleanly with `npm run verify:docs`.

## Next Step

Use V3 as the comparator for the next Billy architecture experiment.
