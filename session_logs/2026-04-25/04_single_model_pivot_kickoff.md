# Single Model Per Band — Architecture Pivot Kickoff

## Goal

- Open `feat/single-model-per-band` branch and document the full architectural
  direction before any code work begins.
- Lock the design decisions (precision@25 metric, per-band predictor classes,
  new Supabase tables, frontend simplification) in writing.

## Constraints

- No code changes in this session — documentation only.
- Legacy tables and multi-model pipelines remain untouched on `main`/`dev`.
- All new artifacts live on `feat/single-model-per-band`.

## Files And Artifacts

- `docs/contributor/adr/0001-single-model-per-band.md` — new ADR
- `.agent/AGENTS.md` — updated rule 4 (band-agnostic reframe)
- `.agent/PLAYBOOK.md` — updated rule 3
- `.agent/CONTEXT.md` — updated "Repo Rules That Matter Most"
- `docs/contributor/developer_guide/architecture.md` — updated Models/Evaluation, routes, non-negotiables, Model Platform
- `docs/user/pipeline_usage.md` — added branch note on `--model` flag
- `docs/reference/schemas/unified_tables.md` — added planned new table schemas
- `docs/operations/data_recovery_rebuild.md` — added branch context note
- `README.md` — updated website feature list and Key Components

## Validation

- Reviewed all docs match ADR 0001 intent.
- `git diff --stat` shows only documentation files changed.

## Next Step

- Connor reviews the documentation on this branch.
- After sign-off, begin Phase A implementation: new Supabase migration,
  registry reshape, storage helpers, pipeline script updates, frontend.
- Open items to resolve before first code commit (see plan file):
  - Confirm `setlist_*` table names or propose alternatives.
  - Confirm precision@25 weighted-blend formula.
  - Confirm per-band `top_n` defaults for small-repertoire bands.
  - Decide Phase B promotion threshold (suggest ≥3% absolute precision@25
    over 50 shows vs. legacy best-of-three).
