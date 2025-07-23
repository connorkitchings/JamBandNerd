Quality Gates

> 📚 For the entry point to all documentation and standards, see [README.md](../../README.md).
> **Tooling Note:** JamBandNerd recommends [uv](https://github.com/astral-sh/uv) as the Python
package manager. Use Python 3.12.x for best compatibility (especially for lxml). Install all
dependencies with `uv pip install .` (from `pyproject.toml`).

This document contains the checklists and standards that ensure every piece of work is high-quality,
consistent, and secure before it's integrated.

1. Pre-Commit Checklist
Run this checklist before every git commit.

[ ] Code is formatted: Ran black . or prettier --write .

[ ] Linter passes: Ran ruff . or eslint . with zero errors.

[ ] Code is self-documented: Variables and functions have clear, intention-revealing names.

[ ] No commented-out code: Dead code has been removed.

[ ] No hardcoded secrets: API keys (e.g., PHISH_API_KEY), passwords, etc., are loaded from a .env file
using python-dotenv.

[ ] Commit message is descriptive: Follows the convention in project_context.md.

[ ] Band pipeline completion is logged to logs/data_collection.log (see logger.py and run_all.py).

1. Pre-Merge Checklist (Pull Request)
Run this more thorough checklist before merging a feature branch into main.

[ ] All Pre-Commit checks pass.

[ ] Feature works as intended: Manually tested the primary user flow.

[ ] Unit tests are written and passing: All new logic is covered by tests.

[ ] Test coverage has not decreased: Run coverage report.

[ ] Relevant documentation is updated: prd.md, project_context.md, or README.md have been updated if
necessary.

[ ] Security checklist is reviewed: See section 3 below.

[ ] No "TODO" comments remain: All temporary todos have been resolved or converted to tasks in
implementation_schedule.md.

2. Security Review Checklist
A mandatory review for any feature handling user input, authentication, or data.

JamBandNerd handles only public band setlist/show data. No personal user data is collected or stored.

Input & Data Validation
[ ] All data sources are validated for schema consistency and expected values.

[ ] SQL injection is prevented (using parameterized queries/ORMs) if any database access is added in
future.

[ ] Cross-Site Scripting (XSS) is not applicable (no user-facing web input), but output is properly
encoded/escaped if web features are added.

[ ] All outputs (CSV, JSON) are saved to the correct `3_DataStorage/<band>/Collected/` subdirectories.

Authentication & Authorization
[ ] No authentication or user accounts are present in the current system. If added, follow secure
password and access control practices.
[ ] No authentication or user accounts are present in the current system. If added, follow secure
password and access control practices.

Error Handling & Logging
[ ] Error messages shown to users (if any) are generic and do not leak internal system details
(e.g., stack traces).

[ ] Sensitive information (passwords, API keys) is not present in logs.

3. Definition of Done (DoD)
This is the global standard for any task to be marked as "Done" in the implementation_schedule.md.

A task is considered Done only when:

All code has been merged into the main branch.

All checks in the Pre-Merge Checklist are complete.

The feature has been deployed to a staging or production environment.

The corresponding task in implementation_schedule.md is marked as ✅ Done.
