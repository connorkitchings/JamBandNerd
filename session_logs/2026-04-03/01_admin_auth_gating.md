# Session Log: Admin Auth Gating

**Date**: 2026-04-03
**Branch**: `fix/admin-auth-gating`
**Session type**: Security fix

## Goal

Gate the `/admin/*` pages and `/api/admin/*` routes at the server layer. Previously, admin HTML/JS was served to any visitor; auth was only checked client-side and independently at each API route.

## Constraints

- No changes to the existing HMAC session cookie system (it works, just missing a gate layer)
- Must not break the login flow (`/api/admin/session` must remain publicly reachable)
- Next.js 16.2.0 on Vercel

## Commands Run

```bash
npm run lint:web    # passed
npm run build:web   # passed
```

Python pipeline tests not run (no Python changes in this session).

## Files Changed

| File | Change |
|------|--------|
| `apps/web/src/proxy.ts` | NEW — Next.js 16 proxy (replaces middleware.ts convention). Gates `/admin/*` and `/api/admin/*`. Returns 401 for API routes, redirects page routes to `/admin/setlist?auth=required`. |
| `apps/web/src/app/admin/layout.tsx` | NEW — Thin admin layout wrapper with "ADMIN" header strip. |
| `apps/web/src/app/api/admin/session/route.ts` | Fixed password comparison: replaced `!==` with `timingSafeEqual` (constant-time). |
| `apps/web/.env.local.example` | Added `ADMIN_SESSION_SECRET` entry (was missing, required by auth system). |

## Validation Status

- ESLint: ✅ passed
- Next.js build: ✅ passed (no warnings)
- Manual smoke: not run (requires local `.env.local` with `ADMIN_PASSWORD` + `ADMIN_SESSION_SECRET`)
- Python tests: ⬜ skipped (no Python changes)

## Key Finding

Next.js 16 deprecated `middleware.ts` in favour of `proxy.ts` with a `proxy` named export. The proxy always runs on the Node.js runtime — no `export const runtime` or `export const config` are permitted. Route matching must be done inside the function.

## Next Step

Remaining 3 fixes from the session plan:
- Fix 2: Hybrid prediction storage cleanup (`fix/prediction-storage-cleanup`)
- Fix 3: Unify Phish `show_id` (`fix/unify-phish-show-id`)
- Fix 4: WSP scraper versioning (`fix/wsp-parser-versioning`)
