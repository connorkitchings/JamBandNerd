## Session 2026-05-02 — Local Supabase Access For Website Review

## Goal
Get the local website to read real Supabase tables instead of falling back to the missing-env state during local review.

## Constraints
- Keep real Supabase data as the default path.
- Do not commit secrets.
- Preserve the production-only rejection of secret-style anon keys on Vercel.
- Stop once the user requested a wrap-up and commit.

## Commands Run
- `npm run build:web`
- `npm run dev -- --port 3001` from `apps/web`
- `curl` checks against `/`, `/predictions?band=goose&model=deal`, `/last-show?band=goose`
- Direct `node` checks against the Supabase client and local env file parsing

## Files Changed
- `apps/web/src/lib/supabase/server.ts`
- `apps/web/src/lib/data/bands.ts`
- `README.md`
- `apps/web/README.md`
- `docs/contributor/supabase_local_dev.md`
- `docs/operations/website_delivery.md`
- `.agent/PLAYBOOK.md`
- `.env.local` created locally for the website runtime

## Validation Status
- `npm run build:web` passed earlier in the session before the last env-loader change.
- Local Supabase reads work in a standalone Node query.
- The live Next dev server still reported the website fallback state when I stopped, so the last runtime verification is incomplete.

## Next Step
Restart the website from a clean build and verify the homepage and route-level prediction pages render real Supabase data instead of the missing-env fallback.
