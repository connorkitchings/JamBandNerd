# Session 04 — Rollback Deal Promotion

**Date**: 2026-04-10
**Role**: Navigator
**Branch**: `dev` (local), PRs targeting `main`

## Goal

Roll back today's merged PRs (#29 Deal promotion, #30 import fix) from `main` while preserving two valuable, model-agnostic changes extracted from PR #29.

## Constraints

- CK+ Supabase tables (`predictions_ckplus`, `accuracy_ckplus`) must remain intact.
- The Tonight! timezone fix and model-test cache framework are independent improvements worth keeping.
- PR #31 (Deal prediction table) should be closed — it depends on the promotion being live.

## Commands Run

```bash
gh pr list --state all --search "created:2026-04-10" --json ...
gh pr close 31
git checkout -b fix/tonight-badge-timezone 0575920   # from pre-PR29 main
git checkout -b feat/model-test-cache 0575920
git checkout -b revert/rollback-april-10-deal-promotion main
git revert -m 1 2d4e68f   # PR #30
git revert -m 1 198f6d9   # PR #29 (conflict in song-board.tsx resolved)
uv run pytest tests/models/test_model_test_cache.py  # 2 passed
git push -u origin <each branch>
gh pr create <each branch>
```

## Files Changed / Artifacts Produced

| PR | Branch | Files | State |
|----|--------|-------|-------|
| #31 | (closed) | — | Closed |
| #32 | `fix/tonight-badge-timezone` | `predictions/page.tsx`, `prediction-hero.tsx` | Open |
| #33 | `feat/model-test-cache` | `model_test_cache.py`, `test_model_test_cache.py` | Open |
| #34 | `revert/rollback-april-10-deal-promotion` | 50 files (revert of PRs #29 + #30) | Open |

## Validation

- `uv run pytest tests/models/test_model_test_cache.py` — 2/2 passed (on cache branch)
- CK+ metadata flags verified as `enabled: true` on revert branch
- Web config `ckplus.enabled: true`, `deal.enabled: false` confirmed on revert branch
- Full quality gates (`black`, `ruff`, `pytest`) not run — all changes are either exact reverts or new standalone modules with passing tests

## Conflict Resolution

`song-board.tsx` conflicted during PR #29 revert because PR #31's Deal-specific additions (ProbabilityBar, isDeal columns) were in HEAD. Resolved by restoring the pre-PR29 version of the file, since PR #31 was closed.

## Next Step

Merge the three open PRs in order: #34 (revert) → #32 (Tonight! fix) → #33 (cache framework). Then rebase `dev` onto the updated `main` before resuming Deal development work.
