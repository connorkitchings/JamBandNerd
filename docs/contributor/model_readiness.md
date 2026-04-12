# Model Readiness Runbook

Use this workflow when preparing a future model for Supabase and eventual
website rollout across the existing active bands.

## Goal

Reach a state where the model has:

- comparison evidence
- canonical prediction rows
- replay lineage in `historical_prediction_runs`
- per-show accuracy in `accuracy_per_show`
- aggregate accuracy in the model aggregate table
- a backend readiness report proving the site can consume it

This does **not** automatically expose the model on the website.

## Canonical command

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase full-readiness
```

Artifacts are written under:

```bash
artifacts/model_readiness/<slug>/
```

## Staged phases

Inspect current readiness without publishing:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase report-only
```

Generate comparison evidence only:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase compare
```

Export local raw snapshots only:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase snapshot
```

Build and publish historical readiness rows from local snapshots:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase backfill-history
```

Compute aggregate accuracy windows:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase aggregate
```

Write the backend readiness report:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase validate
```

## Promotion boundary

`readiness_verified` means the model is ready in Supabase but still hidden from
the product UI.

`web_promoted` is a separate, explicit final step:

1. confirm the readiness report is clean
2. verify `/performance`, `/compare`, and `/replay`
3. update website model visibility metadata

This separation keeps model backfills and site exposure decoupled.
