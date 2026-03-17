# Pipeline Debug

## When To Use

Use when the end-to-end pipeline, a stage, or CI pipeline execution fails.

## Read Order

1. `.agent/CONTEXT.md`
2. `README.md`
3. `docs/user/pipeline_usage.md`
4. `scripts/README.md`
5. `docs/operations/github_actions.md` if CI is involved

## Steps

1. Reproduce with the smallest documented command.
2. Confirm whether the failure is collection, transformation, prediction, validation, or CI-only.
3. Use the consolidated scripts before historical/manual utilities.
4. Capture exact command, environment notes, and the first failing stage.
5. If data correctness is involved, check for `reference_date` misuse and raw-table completeness.

## Expected Artifacts

- Repro command
- Failing file/path or stage
- Minimal fix summary
- Validation command

## Common Mistakes

- Inventing commands not documented in the repo
- Jumping into code changes before reproducing
- Treating stale docs as authoritative over the actual consolidated scripts
