# Model Development Guide

This guide explains how to add or remove backend prediction models using the
registry-based model platform.

## Canonical Source of Truth

Backend model registration is defined in:

- `src/jambandnerd/models/registry.py`

The registry controls:

- model slug and display name
- predictor class instantiation
- model version and legacy prediction table mapping
- pipeline/backfill/validation/web inclusion flags
- prediction serialization function

Website config in `apps/web/src/lib/config.ts` is presentation metadata only.
It is not backend model registration.

`src/jambandnerd/config/models.py` and `src/jambandnerd/config/database.py`
remain compatibility shims for legacy callers and are derived from registry
metadata.

## Add a New Backend Model

1. Create a model package:
`src/jambandnerd/models/<slug>/model.py`.

2. Implement a predictor class that inherits `PredictionModel` and consumes
`ModelData`.

3. Add a model-specific serialization helper:
`src/jambandnerd/models/<slug>/serialization.py` with
`serialize_predictions(predictions) -> list[dict]`.

4. Add one `ModelDefinition` entry in
`src/jambandnerd/models/registry.py`.

5. Optionally add website presentation metadata in
`apps/web/src/lib/config.ts` if the model should be visible in product
surfaces.

## Remove or Disable a Model

Use the registry flags first:

- `enabled_for_pipeline=False`
- `enabled_for_backfill=False`
- `enabled_for_accuracy_validation=False`
- `enabled_for_web=False`

Then remove package code once no runtime paths depend on it.

## Experimental Model Promotion

For experimental models (for example Deal), keep these flags disabled until
promotion evidence is documented:

- `enabled_for_pipeline=False`
- `enabled_for_backfill=False`
- `enabled_for_accuracy_validation=False`
- `enabled_for_aggregate_accuracy=False`
- `enabled_for_web=False`

Promotion evidence should come from the canonical comparison workflow:

```bash
uv run python scripts/compare_models.py --candidate-model <slug> --band all --fresh-training
```

Promotion evidence should include:

- current standard window: `last_50`
- metric bundle at `K=10/25/50`: `hit_rate`, `avg_matches`, `precision`, `recall`, `f1`
- per-band results, cross-band averages, and candidate-minus-baseline deltas
- explicit promotion-gate outcomes versus CK+

Experimental feature work should also start with a shared-input audit:

```bash
uv run python scripts/audit_shared_model_inputs.py --band all
```

Only fields that can be normalized for every active band should move into the
shared model core.

## Capability Flags

`ModelDefinition` capability fields control orchestration behavior:

- `supports_training`: script flows may call `train()`.
- `supports_live_predictions`: model can generate live prediction boards.
- `supports_backtest`: model can run historical replay/backtest.

Inclusion flags control where the model is active:

- `enabled_for_pipeline`
- `enabled_for_backfill`
- `enabled_for_accuracy_validation`
- `enabled_for_web`

## Testing Checklist

- Unit test model ranking and serialization shape.
- Run script-level tests that rely on registry-driven model selection.
- Verify no script adds slug-specific branching for registration decisions.
- For experimental models, add or update comparison-report and promotion-gate
  regression tests.

Suggested commands:

```bash
uv run ruff check src tests scripts
uv run pytest tests/models tests/pipeline/test_run_backtest.py tests/pipeline/test_run_optimized_pipeline.py
uv run pytest tests/pipeline/test_compare_models.py
```
