# 2026-03-19 Session Log 10

## Goal
Deploy the `apps/web` application to Vercel and configure the live environment to connect to Supabase. Also, set up the local development environment for the web app to verify it runs properly.

## Constraints
- Deploy using the Vercel CLI from the terminal.
- Ensure the `SUPABASE_URL` and `SUPABASE_KEY` are passed to both the Production and Preview environments in Vercel securely (excluding Development).
- Set up `apps/web/.env.local` properly so Next.js running via the workspace command from the root picks up the environment variables.

## Commands Run
```bash
npx vercel link --yes
npx vercel --yes
npx vercel env add SUPABASE_URL
npx vercel env add SUPABASE_KEY
npx vercel --prod
cp apps/web/.env.local.example apps/web/.env.local
npm run dev:web
```

## Files Changed Or Artifacts Produced
- `.vercel/` directory generated locally for project linking.
- `.gitignore` updated automatically by Vercel to ignore `.vercel`.
- `apps/web/.env.local` created with correct Supabase credentials.
- New Playbook entry added for Next.js `.env.local` placement in a monorepo setup.

## Validation Status
- Vercel CLI successfully authenticated and linked project: `connorkitchings-projects/web` ✅
- Vercel deployment succeeded with environment variables passed to Production and Preview ✅
- `npm run dev:web` successfully started the local development server on port 3000 without missing environment variable errors ✅

## Next Step
Begin making iterative changes to the Next.js UI in `apps/web` now that the local workflow and production deployment pipeline are established.
