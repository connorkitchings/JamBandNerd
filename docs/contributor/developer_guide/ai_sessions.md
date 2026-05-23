# Agentic Development

JamBandNerd uses a canonical multi-tool workflow for AI-assisted development. This document is the contributor-facing map to that stable system.

## Canonical Entry Points

- `AGENTS.md` -> `.agent/AGENTS.md`
- `CLAUDE.md` -> `AGENTS.md`
- `GEMINI.md` -> `AGENTS.md`
- `.agent/CONTEXT.md` for the startup router
- `.agent/skills/CATALOG.md` for reusable task workflows
- `.codex/QUICKSTART.md` for copy-paste commands

## Boot Order

AI tools should load these first:

1. `pyproject.toml`
2. `README.md`
3. `docs/user/pipeline_usage.md`
4. `docs/contributor/developer_guide/architecture.md`
5. `.agent/CONTEXT.md`

Everything else should be loaded on demand.

## Session Workflow

### Start

1. Read `.agent/CONTEXT.md`
2. Check `git status --short`
3. Read the boot-order files only
4. Load a matching skill from `.agent/skills/CATALOG.md`
5. Check the latest relevant file in `session_logs/` if continuity matters

### End

1. Run the relevant validation commands from `.agent/workflows/health-check.md`
2. Update any affected docs
3. Write a session log to `session_logs/YYYY-MM-DD/NN.md`
4. Add any durable lesson to `.agent/PLAYBOOK.md`

## Session Log Template

Use `session_logs/TEMPLATE.md` for the canonical structure.

Historical logs in `docs/logs/` remain available as archive only.

## Repo-Specific Guardrails

- Use `README.md` and `docs/user/pipeline_usage.md` as the command source of truth
- Preserve the `reference_date` cutoff for all feature engineering and backtesting
- Keep transformations in memory through `ModelData`
- Keep band-specific logic in collectors, not shared transforms or models
