# Agent Playbook

This file stores persistent lessons and operating patterns that should survive across sessions.

## Rules

1. Treat `README.md` and `docs/user/pipeline_usage.md` as the command source of truth.
2. Preserve the `reference_date` anti-leakage boundary in any transformation or modeling change.
3. Keep shared pipeline code band-agnostic; push source-specific behavior into collectors.
4. Prefer consolidated scripts in `scripts/` before reaching for historical or manual utilities.
5. If you change agent workflows, update `.agent/`, `README.md`, and relevant contributor docs together.

## Strategies

1. Use a small boot order and fetch docs on demand to avoid context bloat.
2. Treat `docs/logs/` as archive/history and `session_logs/` as the active session system.
3. Keep quality gates explicit and copy-pasteable so every AI tool uses the same validation path.

## Success Patterns

- Start from `.agent/CONTEXT.md`, not from broad repo search.
- Use `scripts/README.md` when reconciling which scripts are canonical vs manual/admin.
- When guidance drifts, fix the root entrypoints first and update downstream docs second.
- For freshness or orphan checks, validate only completed shows; including today or future scheduled shows creates false positives that look like ingestion failures.
