# Model Readiness Runbook (Legacy — Multi-Model Era)

> **This runbook documents the old multi-model readiness path.** It is preserved
> as historical reference only. The multi-model architecture was retired with
> ADR 0001 (complete, v1.0.1 live).
>
> For current Phase B per-band model iteration, see
> [Model Development Guide](model_development.md#staged-model-promotion).

Use this workflow when reviewing legacy model promotion history or running
offline baseline comparisons against legacy tables.

## Goal

This legacy workflow reached a state where a model had:

- comparison evidence
- canonical prediction rows
- legacy replay lineage in `historical_prediction_runs` (no longer populated by active pipeline)
- legacy per-show accuracy in `accuracy_per_show` (no longer populated by active pipeline)
- a backend readiness report proving the site could consume it

This did **not** automatically expose the model on the website.

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

## Active Model Issues

- **Goose probability calibration:** local V1 review found a next-show Goose
  prediction showing Hungersite at `100%`. Song-level setlist probabilities
  should not reach 100%, so investigate the Goose model probability calculation
  or calibration layer before treating displayed Goose percentages as
  trustworthy.
- **Non-Goose LTP serialization:** latest prediction payloads for Phish, WSP,
  Billy, and UM do not include `LTP`/`last_played_date`, so the website cannot
  render last-played dates for those bands. Supabase source checks found raw
  last-played data for Phish, WSP, and Billy, while UM likely needs
  transform-derived LTP from setlists. Treat this as a prediction
  generation/serialization follow-up, not a frontend display issue.
