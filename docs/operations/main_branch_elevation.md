# Main Branch Elevation

This runbook documents the production gate for `main`.

## Target policy

- `main` is the only production branch.
- No direct pushes to `main`.
- All production changes merge through pull requests.
- Passing automation is required before merge.

## GitHub ruleset to apply manually

Create a branch ruleset for `main` with these settings:

- Require a pull request before merging.
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Require status checks before merging.
- Required checks:
  - `Repo Quality / Verify Repository`
  - `Website Quality / Verify Website`
- Block force pushes.
- Block branch deletion.

This repository cannot enforce those remote GitHub settings from code alone, so the ruleset must be applied in the GitHub UI.

## Release flow

1. Open a pull request into `main`.
2. Confirm Vercel preview deployment is healthy.
3. Wait for `Repo Quality` and `Verify Website` to pass.
4. Resolve review conversations.
5. Merge to `main`.
6. Confirm the Vercel production deploy succeeds.
7. Run hosted smoke verification against production.

## Post-deploy verification

- `/`
- `/predictions`
- `/performance`
- `/compare`
- `/replay`
- `/last-show`

Run:

```bash
SMOKE_BASE_URL=https://jambandnerd.com npm run test:web:smoke:hosted
```

## Rollback

1. Revert the offending pull request on GitHub.
2. Merge the revert into `main`.
3. Confirm the new production deployment completes.
4. Re-run hosted smoke verification.
