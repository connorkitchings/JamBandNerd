# JamBandNerd Web

This app is the website foundation for JamBandNerd.

## Commands

```bash
npm install
npm run dev:web
npm run lint:web
npm run build:web
```

## Build Defaults

- Use Server Components by default.
- Read Supabase on the server for core product views.
- Keep client-side state light and URL-driven.
- Design mobile-first and avoid clipped table content.
- Add dependencies conservatively; bundle size matters from the start.
- Treat Google Stitch exports as the visual source of truth for dashboard/layout work, but translate them into typed React components instead of dropping raw static markup into routes.
