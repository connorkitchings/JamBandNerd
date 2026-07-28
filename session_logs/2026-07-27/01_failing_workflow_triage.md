# Failing Workflow Triage + Dependabot Sweep

## Goal

- Identify currently failing GitHub Actions workflows and ship the fixes.
- Triage the backlog of open Dependabot PRs against the freshly-stabilized baseline.

## Constraints

- Do not work directly on `main`. Use feature branches or Dependabot PRs.
- No database schema, model behavior, or website API changes.
- Each merged change must keep `npm run verify:python` and `npm run verify:docs` green.
- Final `main` must pass the Dependency Audit workflow (no known PyPI vulnerabilities).

## Findings

### Failing workflows on `main` (start of session)

| Workflow | Last failures | Root cause |
| --- | --- | --- |
| Dependency Audit (weekly Mon) | 2026-07-20, 2026-07-27 | `soupsieve 2.7` flagged with PYSEC-2026-3071 + PYSEC-2026-3072 (fix version >=2.8.4). |
| Daily Data Pipeline | 2026-07-17, 2026-07-18 (recent runs green only because WSP did not lag) | WSP `degraded_upstream_lag` (EC setlist publication delay) treated as a hard accuracy-freshness failure. |

### Pre-existing local fix that had never been shipped

Branch `codex/repo-review-stabilization` (2 commits ahead of `main`, never pushed):

- `54c5b5d8` (2026-07-10) Stabilize repo verification and band scopes (band matrix becomes repo-authoritative via `scripts/get_all_bands.py`; shared matrix features consolidated into `src/jambandnerd/models/shared/matrix_features.py`).
- `9307514c` (2026-07-24) fix(ci): handle WSP lag accuracy warnings. Includes the `soupsieve` 2.7 -> 2.9.1 bump and scopes `--skip-accuracy` to manual dispatches + WSP `degraded_upstream_lag` in both freshness audits.

## Commands Run

```bash
# Pre-merge validation on the feature branch
npm run verify:python   # 611 passed, 10 deselected
npm run verify:docs     # exit 0

# Ship the fix branch
git push -u origin codex/repo-review-stabilization
gh pr create --base main --head codex/repo-review-stabilization --title "fix(ci): stabilize repo verification + WSP lag + dependency audit" --body "<see PR #184>"
gh pr checks 184 --watch --interval 15
gh pr merge 184 --merge --delete-branch

# Confirm Dependency Audit is green on new main
gh workflow run dependency-audit.yml --ref main
gh run watch <run-id> --exit-status

# Merge Dependabot PRs in risk order (3 GitHub Actions + 5 Python deps)
gh pr merge 181 --merge   # actions/cache 5 -> 6
gh pr merge 182 --merge   # actions/setup-python 6 -> 7
gh pr merge 183 --merge   # actions/setup-node 6 -> 7
gh pr merge 178 --merge   # ruff 0.15.19 -> 0.15.20
gh pr merge 177 --merge   # typer 0.26.6 -> 0.26.8
gh pr merge 179 --merge   # duckdb 1.5.3 -> 1.5.4
gh pr merge 170 --merge   # pymdown-extensions 10.21.2 -> 11.0
gh pr merge 180 --merge   # beautifulsoup4 4.14.3 -> 4.15.0

# Post-merge baseline check on new main
uv sync --extra dev
npm run verify:python     # 611 passed, 10 deselected
npm run verify:docs       # exit 0
gh workflow run dependency-audit.yml --ref main   # final audit
```

## Files And Artifacts

- PR #184 (merged `ad91e71e`): branch `codex/repo-review-stabilization` with both the audit/WSP fix and repo stabilization.
- PRs #181, #182, #183, #178, #177, #179, #170, #180 merged into `main` (final HEAD `1fc72a65`).
- Workflow run <https://github.com/connorkitchings/JamBandNerd/actions/runs/30298645608> final Dependency Audit on new `main` HEAD.

## Validation

- `verify:python`: 611 passed, 10 deselected (live tests deselected by config).
- `verify:docs`: docs build clean, exit 0.
- Dependency Audit workflow on `1fc72a65` (post-merge HEAD): `success` with no known vulnerabilities.
- PR #184 CI on Vercel + Verify Repository + Verify Website + GitGuardian all green before merge.

## Next Step

- Confirm the next scheduled Monday Dependency Audit (2026-08-03) stays green.
- Watch the next WSP `degraded_upstream_lag` event in the daily pipeline to confirm the scoped `--skip-accuracy` path emits a warning rather than a hard failure.
- No outstanding Dependabot PRs at end of session.
