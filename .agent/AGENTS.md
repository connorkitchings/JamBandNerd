# JamBandNerd Agent Operating Manual

This file defines how AI coding tools should work in this repository. Keep it short, current, and aligned with the actual repo state.

## Entry Flow

1. Read `.agent/CONTEXT.md`.
2. Read only the files in the boot order.
3. Load one skill from `.agent/skills/CATALOG.md` if the task matches.
4. Check the latest log in `session_logs/` if prior session context matters.

## Agent Roles

### Navigator
- Triage the request.
- Write a short plan before substantial work.
- Keep the startup context budget small.
- Route to a specialist mindset when the task is clearly data, model, web, or docs heavy.

### DataOps
- Own collectors, scripts, Supabase, CI diagnostics, and data freshness checks.
- Preserve idempotent writes and existing script interfaces.

### Feature Engineer
- Own transformations, shared pipeline logic, and correctness fixes.
- Guard against leakage and band-specific creep into the shared core.

### Modeler
- Own model behavior, backtests, metrics interpretation, and regression analysis.
- Return compact metric deltas and verification commands.

### Web/App
- Own the website delivery strategy, frontend architecture, and legacy Streamlit transition work.
- Prefer changes that move the repo toward the website target over new Streamlit-only feature work.

### Researcher
- Gather current external information with citations when needed.
- Return concise findings with risks and gaps called out.

## Boot Order

Read these first and avoid bulk-loading other docs:

1. `pyproject.toml`
2. `README.md`
3. `docs/user/pipeline_usage.md`
4. `docs/contributor/developer_guide/architecture.md`
5. `.agent/CONTEXT.md`

Open on demand:
- CI/CD: `docs/operations/github_actions.md`
- Website delivery: `docs/operations/website_delivery.md`
- WSP fallback: `docs/operations/tourwrangler_fallback.md`
- Historical archive: `docs/logs/`

## Critical Rules

1. Use `README.md` and `docs/user/pipeline_usage.md` as the source of truth for commands.
2. Do not create intermediate Supabase tables. Transform data in memory through `ModelData`.
3. All feature engineering must respect `reference_date`. Never use future data in features or backtests.
4. Band-specific collector logic belongs in `src/jambandnerd/data_collection/{band}/`. Per-band predictor classes are allowed under `src/jambandnerd/models/{band}/` as the platform transitions to a single precision-optimized model per band (see ADR 0001). Shared infrastructure — `ModelData`, `PredictionModel` ABC, training/eval harness, storage contract — remains band-agnostic.
   - **On `feat/single-model-per-band`**: The backend write boundary is `setlist_*` (one row per band per show, no `model_slug`). See ADR 0001 and `docs/reference/schemas/unified_tables.md`.
5. Prefer the consolidated scripts in `scripts/` over one-off or historical entrypoints.
6. Never work directly on `main`. Use a feature branch.
7. Every logic change needs tests or a documented reason why no tests apply.
8. Update docs when behavior, workflows, or entrypoints change.
9. Record a session log in `session_logs/` when a development session materially changes the repo.

## Working Loop

1. Confirm the task and constraints.
2. Read only the boot-order files first.
3. Run the smallest useful command.
4. Keep artifacts small: file paths, commands, tables, and metrics.
5. If blocked after two solid attempts, escalate with a concise handoff packet.

## Handoff Packet

Use this format when passing work across tools or specialist mindsets:

```text
[Agent] -> [Next Agent]: goal + artifact path + open question
```

Example:

```text
Modeler -> Feature Engineer: Backtest dropped after recency tweak.
Check src/jambandnerd/transformations/gaps.py and tests/test_models.py. Is the reference_date cutoff still applied before feature aggregation?
```

## Definition Of Done

- Small, focused diff
- Tests run or explicitly skipped with reason
- Canonical commands still documented accurately
- Relevant docs updated
- Session log updated if the session materially changed the repo
- No secrets committed

## Quality Gates

Run these before shipping non-trivial changes:

```bash
npm run verify:python
npm run verify:docs
npm run verify:web
```

On a clean baseline, finish with:

```bash
npm run verify:clean
```

Use narrower commands during iteration when appropriate, but keep the verify entrypoints as the canonical full check.
