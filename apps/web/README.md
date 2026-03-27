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
- Keep `@/lib/data` as the stable import surface while new domain ownership lives under `src/lib/data/{bands,predictions,accuracy,replay,shows,venues}.ts`.
- Design mobile-first and avoid clipped table content.
- Use safe-area-aware mobile navigation and content padding.
- Keep dense data views on a shared responsive table pattern.
- Add dependencies conservatively; bundle size matters from the start.
- Prefer local/system font stacks over remote build-time font fetches so CI and offline builds stay reproducible.
- Treat Google Stitch exports as the visual source of truth for dashboard/layout work, but translate them into typed React components instead of dropping raw static markup into routes.
- Use `/preview/tables` as an internal QA route for responsive table verification and smoke tests.

## Web Architecture

- `src/app/**` owns route composition and metadata.
- `src/components/**` owns shared UI and interactive islands.
- `src/lib/data.ts` remains the compatibility barrel for route imports.
- `src/lib/data/*.ts` owns server-side reads by domain: bands, predictions, accuracy, replay, shows, and venues.
- `src/lib/supabase/server.ts` is the single server-side Supabase entry point.
- `"use client"` is reserved for interactive controls, navigation hooks, and live subscriptions.

## Deployment Defaults

- Vercel with native GitHub integration is the target deployment path.
- The Vercel project should use `apps/web` as its root directory.
- `main` is the production branch.
- Preview deployments should come from pull requests and non-`main` branches.
- The website expects `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
- Do not use a service-role secret in the website environment.
- The internal admin setlist flow additionally requires `ADMIN_PASSWORD` and `ADMIN_SESSION_SECRET`, and now authenticates through an httpOnly session cookie.
