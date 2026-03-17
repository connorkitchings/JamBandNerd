# Session Handoff Workflow

Use this when switching tools or ending a session that another tool or engineer will pick up.

## Handoff Packet

```text
[Agent] -> [Next Agent]: goal + artifact path + open question
```

## Required Artifacts

- Latest session log in `session_logs/YYYY-MM-DD/NN.md`
- Exact commands run
- Validation status
- Specific next step

## Retrieval Order For The Next Tool

1. `.agent/CONTEXT.md`
2. Latest relevant file in `session_logs/`
3. Any files named in the handoff packet

## Archive Note

Older logs in `docs/logs/` are historical context only. New handoffs belong in `session_logs/`.
