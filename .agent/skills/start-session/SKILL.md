# Start Session

## When To Use

Use at the beginning of a new coding session or after losing context.

## Steps

1. Read `.agent/CONTEXT.md`.
2. Read the boot-order files only.
3. Check `git status --short` to understand local state.
4. If the task depends on recent prior work, open the latest file in `session_logs/`.
5. State a short plan before substantial edits.

## Outputs

- Short plan
- Any key constraints or repo-state risks called out up front

## Common Mistakes

- Loading the whole docs tree immediately
- Treating `docs/logs/` as the active handoff system
- Ignoring unrelated dirty worktree changes
