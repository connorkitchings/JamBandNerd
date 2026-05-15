# Branch Consolidation Wrap

## Goal

Consolidate active development onto `feat/single-model-per-band`, leaving only
`main`, `dev`, and `feat/single-model-per-band` as local and remote branches.

## Constraints

- Preserve `main` and `dev`.
- Do not continue model, schema, or website work during branch cleanup.
- Avoid further merges or cherry-picks after the consolidation point.
- Leave the detached Codex worktree alone.

## Commands Run

```bash
git status --short --branch
git branch --format='%(refname:short)'
git branch -r --format='%(refname:short)'
git worktree list
git push origin feat/single-model-per-band
git worktree remove /Users/connorkitchings/Desktop/Repositories/JamBandNerd-dev
git branch -D feat/wsp-combo-sweep fix/prefer-future-predictions fix/weekly-correction-sweep
git push origin --delete fix/prefer-future-predictions fix/weekly-correction-sweep
git push origin --delete dependabot/npm_and_yarn/eslint-config-next-16.2.6 dependabot/npm_and_yarn/playwright/test-1.60.0 dependabot/npm_and_yarn/react-19.2.6
git push origin --delete dependabot/npm_and_yarn/react-dom-19.2.6 dependabot/npm_and_yarn/tailwindcss-4.3.0 dependabot/uv/mypy-2.1.0
git push origin --delete dependabot/uv/pandas-3.0.3 dependabot/uv/pymdown-extensions-10.21.3 dependabot/uv/requests-2.34.0 dependabot/uv/types-requests-2.33.0.20260513
git fetch --prune origin
```

Earlier in the consolidation, `feat/wsp-combo-sweep`, the unique weekly
correction workflow commit, and the useful non-stale prefer-future prediction
commits were merged or cherry-picked into `feat/single-model-per-band`.

## Files Changed Or Artifacts Produced

- Added this session log.
- No source code changes were made during the final remote branch cleanup pass.

## Validation Status

Branch/state checks passed:

- Current branch is `feat/single-model-per-band`.
- Worktree is clean and synced with `origin/feat/single-model-per-band`.
- Local branches are exactly:
  - `main`
  - `dev`
  - `feat/single-model-per-band`
- Remote branches are exactly:
  - `origin/main`
  - `origin/dev`
  - `origin/feat/single-model-per-band`
- Detached Codex worktree remains present and untouched.

No code tests were rerun for the final branch deletion pass because it only
deleted remote refs. The consolidated branch had already passed the focused
Python checks and `npm run verify:web` before cleanup.

## Next Step

Open/review the `feat/single-model-per-band` PR against `dev`, then merge to
`dev` before promoting to `main`.
