# Contributing

JamBandNerd supports both human contributors and AI coding tools. This document is the high-level workflow; the canonical AI operating details live under `.agent/`.

## First Reads

- Humans: `README.md`, `docs/user/pipeline_usage.md`, `docs/contributor/onboarding.md`
- AI tools: `AGENTS.md` -> `.agent/AGENTS.md` -> `.agent/CONTEXT.md`

## Workflow

1. Create a feature branch. Do not work directly on `main`.
2. Use documented commands from `README.md` and `docs/user/pipeline_usage.md`.
3. Make the smallest useful change.
4. Add or update tests when logic changes.
5. Update docs when commands, workflows, or behavior change.
6. Run the health checks before shipping non-trivial work.

## Health Checks

```bash
uv run black src tests scripts
uv run ruff check src tests scripts
uv run pytest
```

## Project Rules

- Respect `reference_date` in all feature engineering and backtesting.
- Do not create intermediate Supabase tables.
- Keep band-specific logic in collectors under `src/jambandnerd/data_collection/`.
- Prefer consolidated scripts in `scripts/` over historical/manual one-offs.

## AI Session Logging

Active AI session logs belong in `session_logs/`.

Historical development logs remain in `docs/logs/` as archive only.
