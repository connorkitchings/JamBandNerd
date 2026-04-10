# End Session

## When To Use

Use before finishing a meaningful development session.

## Steps

1. Run the relevant validation commands or explicitly document what was not run.
2. Update docs affected by the session.
3. Create or update `session_logs/YYYY-MM-DD/NN.md`.
4. Add a reusable lesson to `.agent/PLAYBOOK.md` if the session exposed a durable pattern.
5. Bump the version if the session delivered a meaningful feature or breaking change:
   - Patch (`0.x.y` → `0.x.y+1`): bug fixes, small improvements
   - Minor (`0.x.y` → `0.x+1.0`): new features, model promotions, significant additions
   - Update both `pyproject.toml` and `apps/web/package.json` together.
6. Leave a one-line next step in the log.

## Required Log Content

- Goal
- Constraints
- Commands run
- Files changed or artifacts produced
- Validation status
- Next step

## Common Mistakes

- Finishing without a session log
- Leaving entrypoint docs stale after changing workflow
- Hiding skipped validation
