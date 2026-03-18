# Node 24 Actions Upgrade

## Goal

- Remove the GitHub Actions runner warning about Node 20-based JavaScript actions in the daily pipeline workflow.

## Constraints

- Keep the workflow behavior unchanged aside from upgrading maintained action versions.
- Use currently published upstream releases as the source of truth.

## Commands Run

```bash
gh release view --repo actions/checkout --json tagName,name,publishedAt
gh release view --repo actions/setup-python --json tagName,name,publishedAt
rg -n "uses:" .github/workflows/daily-pipeline.yml
git diff -- .github/workflows/daily-pipeline.yml
```

## Files Changed

- `.github/workflows/daily-pipeline.yml`: upgraded `actions/checkout` from `v4` to `v6` and `actions/setup-python` from `v5` to `v6` in all workflow jobs.

## Validation Status

- Confirmed current upstream releases at edit time:
  - `actions/checkout` latest release: `v6.0.2` published 2026-01-09.
  - `actions/setup-python` latest release: `v6.2.0` published 2026-01-22.
- Confirmed all `uses:` references in `daily-pipeline.yml` now point to the `v6` major tags.
- Not yet validated in GitHub Actions execution because the updated workflow has not been committed and pushed, so the last remote run still used the pre-upgrade workflow definition.

## Next Step

- Commit and push the workflow update, then dispatch `daily-pipeline.yml` again to confirm the Node 20 deprecation warning is gone.
