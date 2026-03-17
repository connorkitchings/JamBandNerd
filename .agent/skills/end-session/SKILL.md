# End Session

## When To Use

Use before finishing a meaningful development session.

## Steps

1. Run the relevant validation commands or explicitly document what was not run.
2. Update docs affected by the session.
3. Create or update `session_logs/YYYY-MM-DD/NN.md`.
4. Add a reusable lesson to `.agent/PLAYBOOK.md` if the session exposed a durable pattern.
5. Leave a one-line next step in the log.

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
