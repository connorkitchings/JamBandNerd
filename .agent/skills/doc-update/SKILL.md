# Doc Update

## When To Use

Use when commands, workflows, architecture guidance, or contributor instructions change.

## Steps

1. Identify the canonical source of truth.
2. Update the root entrypoint if the change affects startup guidance.
3. Update downstream docs and navigation next.
4. Run a stale-reference search for renamed paths and retired commands.

## Expected Validation

- `rg` search confirms no stale references remain in the edited scope
- Navigation docs point to current files

## Common Mistakes

- Updating one copy of a command but leaving the others stale
- Treating historical logs as active docs
- Adding duplicate command inventories instead of pointing to canonical docs
