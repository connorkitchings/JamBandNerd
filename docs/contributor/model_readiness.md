# Model Readiness Runbook

> **Legacy runbook**: This workflow documents the old multi-model readiness
> path. On `feat/single-model-per-band`, use it only for rollback context or
> offline baseline comparison while Phase B models are evaluated.

Use this workflow when preparing a legacy model for Supabase and eventual
website rollout across the repo-supported bands.

## Goal

Reach a state where the model has:

- comparison evidence
- canonical prediction rows
- legacy replay lineage in `historical_prediction_runs`
- legacy per-show accuracy in `accuracy_per_show`
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

Write the backend readiness report:

```bash
uv run python scripts/model_readiness.py --model <slug> --band all --phase validate
```

## Promotion boundary

`readiness_verified` means the model is ready in Supabase but still hidden from
the product UI.

Before exposing or trusting the public website surface, run the canonical
website-facing Supabase audit:

```bash
uv run python scripts/audit_supabase_tables.py
```

Interpretation:

- `ok` means the promoted website models have complete live predictions,
  sufficient replay history, sufficient per-show accuracy rows, and healthy
  retained completed-show lineage.
- `warning` means the surface is still readable but supporting issues remain,
  such as intentionally skipped accuracy freshness or missing recent raw
  setlists.
- `failed` means the website-facing prediction or replay contract is incomplete
  and should be fixed before relying on `/predictions` or `/performance`.

Replay completeness is measured against each promoted model's required
readiness window. The audit expects enough unique recent
`historical_prediction_runs.target_show_date` rows, enough `accuracy_per_show`
rows, and enough overlap between promoted models to support paired replay.
Those windows are model-specific registry metadata, not a universal `50`-show
rule. As of the current promoted set, Notebook requires `50` while Deal
requires `10`.

`web_promoted` is a separate, explicit final step:

1. confirm the readiness report is clean
2. confirm `audit_supabase_tables.py` is `ok` for the target bands
3. verify `/predictions`, `/performance`, and `/last-show`
4. update the per-band model registry metadata

This separation keeps model backfills and site exposure decoupled.
