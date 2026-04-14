# Model Development Guide

This guide explains how to add or remove backend prediction models using the
registry-based model platform.

## Canonical Source of Truth

Backend model registration is defined in:

- `src/jambandnerd/models/registry.py`

The registry controls:

- model slug and display name
- predictor class instantiation
- model version and canonical prediction storage metadata
- pipeline/backfill/validation/web inclusion flags
- lifecycle stage, readiness windows, and web visibility state
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

5. Add registry lifecycle metadata for staged rollout:
   - `lifecycle_stage`
   - `web_visibility`
   - `readiness_windows`
   - `readiness_baselines`

6. Optionally add website presentation metadata in
`apps/web/src/lib/config.ts`. Keep new models hidden there until the final
promotion step.

## Remove or Disable a Model

Use the registry flags first:

- `enabled_for_pipeline=False`
- `enabled_for_backfill=False`
- `enabled_for_accuracy_validation=False`
- `enabled_for_web=False`

Then remove package code once no runtime paths depend on it.

## Staged Model Promotion

Future models should follow a staged rollout instead of a one-step platforming
process:

1. `experimental`
2. `readiness_verified`
3. `web_promoted`

For experimental models, keep the execution flags conservative until promotion
evidence is documented:

- `enabled_for_pipeline=False`
- `enabled_for_backfill=False`
- `enabled_for_accuracy_validation=False`
- `enabled_for_web=True` only when the website data/query surfaces should be
  capable of reading the model. This does **not** mean the model is visible in
  the product yet.

The canonical readiness workflow is:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase full-readiness
```

The operator-oriented step-by-step runbook lives in
[`docs/contributor/model_readiness.md`](model_readiness.md).

This workflow is responsible for:

- comparison evidence generation
- local snapshot export for offline historical scoring
- historical canonical prediction + replay lineage publishing
- per-show accuracy publication through `accuracy_per_show`
- backend readiness validation

Use `--phase report-only` to inspect the current state without publishing.

Promotion evidence should come from the readiness workflow's comparison phase
or the canonical comparison workflow:

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

## Final Web Promotion

Backend readiness and public site exposure are intentionally separate.

After readiness is verified:

1. keep the model hidden in `apps/web/src/lib/config.ts`
2. confirm `/performance`, `/compare`, and `/replay` can read the model with
   the current promoted set
3. flip the web visibility metadata in a focused promotion change

This makes it possible to fully backfill and validate a model in Supabase
before users can select it on the site.

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

Lifecycle metadata controls rollout state:

- `lifecycle_stage`
- `web_visibility`
- `readiness_windows`
- `readiness_baselines`

## Testing Checklist

- Unit test model ranking and serialization shape.
- Unit test lifecycle/readiness metadata and staged rollout behavior.
- Run script-level tests that rely on registry-driven model selection.
- Verify no script adds slug-specific branching for registration decisions.
- For experimental models, add or update comparison-report and promotion-gate
  regression tests.
- Run readiness validation tests for the new model lifecycle.

Suggested commands:

```bash
uv run ruff check src tests scripts
uv run pytest tests/models tests/pipeline/test_run_backtest.py tests/pipeline/test_run_optimized_pipeline.py
uv run pytest tests/pipeline/test_compare_models.py
uv run pytest tests/models/test_model_readiness.py tests/pipeline/test_model_readiness.py
```
