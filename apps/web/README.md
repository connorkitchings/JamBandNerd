# JamBandNerd Web

This app is the website foundation for JamBandNerd.

## Commands

```bash
npm install
cp apps/web/.env.local.example apps/web/.env.local
npx playwright install chromium
npm run dev:web
npm run lint:web
npm run build:web
npm run test:web:smoke
```

## Build Defaults

- Use Server Components by default.
- Read Supabase on the server for core product views.
- Keep client-side state light and URL-driven.
- Design mobile-first and avoid clipped table content.
- Use safe-area-aware mobile navigation and content padding.
- Keep dense data views on a shared responsive table pattern.
- Add dependencies conservatively; bundle size matters from the start.
- Treat Google Stitch exports as the visual source of truth for dashboard/layout work, but translate them into typed React components instead of dropping raw static markup into routes.
- Use `/preview/tables` as an internal QA route for responsive table verification and smoke tests.

## Deployment Defaults

- Vercel with native GitHub integration is the target deployment path.
- The Vercel project should use `apps/web` as its root directory.
- `main` is the production branch.
- Preview deployments should come from pull requests and non-`main` branches.
- Local, preview, and production environments all use the same server-side Supabase variable names: `SUPABASE_URL` and `SUPABASE_KEY`.
