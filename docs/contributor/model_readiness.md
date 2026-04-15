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

Before exposing or trusting the public website surface, run the canonical
website-facing Supabase audit:

```bash
uv run python scripts/audit_supabase_tables.py
```

Interpretation:

- `ok` means the promoted website models have complete live predictions,
  sufficient replay history, sufficient per-show accuracy rows, and healthy
  cross-model replay overlap.
- `warning` means the surface is still readable but supporting issues remain,
  such as intentionally skipped accuracy freshness or missing recent raw
  setlists.
- `failed` means the website-facing prediction or replay contract is incomplete
  and should be fixed before relying on `/predictions`, `/performance`, or
  `/replay`.

Replay completeness is measured against each promoted model's required
readiness window. The audit expects enough unique recent
`historical_prediction_runs.target_show_date` rows, enough `accuracy_per_show`
rows, and enough overlap between promoted models to support paired replay.

`web_promoted` is a separate, explicit final step:

1. confirm the readiness report is clean
2. confirm `audit_supabase_tables.py` is `ok` for the target bands
3. verify `/performance`, `/compare`, and `/replay`
4. update website model visibility metadata

This separation keeps model backfills and site exposure decoupled.
