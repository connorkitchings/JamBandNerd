# Fantasy Goose Workflow

**Date**: 2026-04-06
**Branch**: `dev`

---

## Goal

Add a dedicated GitHub Actions workflow that automatically plays Fantasy Goose for Goose using JamBandNerd notebook predictions.

## Constraints

- Keep the existing daily multi-band pipeline intact.
- Use `FG_USER_EMAIL` and `FG_PASSWORD` from environment/secrets.
- Fail closed on missing song mappings or missing exact-date predictions.
- Do not touch the unrelated tracked change in `apps/web/next-env.d.ts`.

## Commands Run

- `sed -n '1,220p' .agent/AGENTS.md`
- `sed -n '1,220p' .agent/skills/start-session/SKILL.md`
- `sed -n '1,260p' README.md`
- `sed -n '1,260p' docs/operations/github_actions.md`
- `git status --short`
- Browser inspection of `https://www.fantasygoose.com/login`, `/entry/create`, and `/entry/mypicks`
- `uv run python scripts/play_fantasy_goose.py --date 2026-04-10 --dry-run`
- `uv run python scripts/play_fantasy_goose.py --date 2026-04-10`
- `uv run pytest tests/test_fantasy_goose.py tests/test_db_operations.py`
- `uv run ruff check src/jambandnerd/__init__.py src/jambandnerd/integrations/fantasy_goose.py src/jambandnerd/integrations/__init__.py scripts/play_fantasy_goose.py tests/test_fantasy_goose.py src/jambandnerd/db/operations.py src/jambandnerd/db/__init__.py tests/test_db_operations.py`

## Files Changed

- `src/jambandnerd/db/operations.py`
- `src/jambandnerd/db/__init__.py`
- `src/jambandnerd/integrations/__init__.py`
- `src/jambandnerd/integrations/fantasy_goose.py`
- `scripts/play_fantasy_goose.py`
- `.github/workflows/fantasy-goose.yml`
- `tests/test_fantasy_goose.py`
- `tests/test_db_operations.py`
- `README.md`
- `docs/operations/github_actions.md`
- `src/jambandnerd/__init__.py`
- `.agent/PLAYBOOK.md`

## Validation

- Added unit coverage for show selection, cutoff handling, name normalization, song mapping, and exact-date prediction lookup.
- Live dry-run for `2026-04-10` resolved a full top 8.
- Live submit for `2026-04-10` created a real Fantasy Goose entry and was verified under `My Picks`.
- Targeted validation passed:
  - `uv run pytest tests/test_fantasy_goose.py tests/test_db_operations.py`
  - `uv run ruff check src/jambandnerd/__init__.py src/jambandnerd/integrations/fantasy_goose.py src/jambandnerd/integrations/__init__.py scripts/play_fantasy_goose.py tests/test_fantasy_goose.py src/jambandnerd/db/operations.py src/jambandnerd/db/__init__.py tests/test_db_operations.py`
- Full repo-wide validation not run in this session.

## Next Step

Run the new GitHub Actions workflow once via `workflow_dispatch` to confirm it reports `already_submitted` for `2026-04-10`, then decide whether to commit and push the branch.
