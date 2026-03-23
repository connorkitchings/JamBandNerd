# 2026-03-23 Session Log 05

## Goal

Make the hosted website smoke workflow compatible with Vercel-protected preview
deployments by adding preview-bypass support while preserving the existing
production verification path.

## Constraints

- Keep production hosted smoke behavior unchanged.
- Use Vercel's documented automation bypass path instead of relying on manual
  preview authentication.
- Fail clearly when a protected preview URL is supplied without the required
  bypass secret.

## Commands Run

```bash
git checkout -b feat-preview-bypass-hosted-smoke
npm run lint:web
npm run build:web
npm run test:web:smoke:list
SMOKE_BASE_URL=https://preview-example.vercel.app npm run test:web:smoke:list
SMOKE_BASE_URL=https://preview-example.vercel.app VERCEL_PROTECTION_BYPASS_TOKEN=fake-token npm run test:web:smoke:list
gh workflow run hosted-web-smoke.yml --ref main -f base_url=https://jambandnerd-git-feat-web-dynami-14cf69-connorkitchings-projects.vercel.app
gh run view 23441638162 --log-failed
gh workflow run hosted-web-smoke.yml --ref main -f base_url=https://jambandnerd-git-feat-web-dynami-14cf69-connorkitchings-projects.vercel.app
gh run view 23441815217 --log-failed
```

## Files And Artifacts

- `apps/web/playwright.config.ts`
- `apps/web/tests/smoke/hosted-target.ts`
- `.github/workflows/hosted-web-smoke.yml`
- `docs/operations/website_delivery.md`
- `session_logs/2026-03-23/05_preview_bypass_hosted_smoke.md`

## Validation

- `npm run lint:web`: passed.
- `npm run build:web`: passed.
- `npm run test:web:smoke:list`: passed for the default production/local config path.
- `SMOKE_BASE_URL=https://preview-example.vercel.app npm run test:web:smoke:list`:
  failed fast with the expected clear error requiring
  `VERCEL_PROTECTION_BYPASS_TOKEN`.
- `SMOKE_BASE_URL=https://preview-example.vercel.app VERCEL_PROTECTION_BYPASS_TOKEN=fake-token npm run test:web:smoke:list`:
  passed config loading, confirming the preview-bypass path activates when the
  token is present.
- GitHub preview smoke reruns on `main` continued to fail with the old
  navigation-missing assertions because the updated preview-bypass code was
  still only present on the local branch and had not been pushed yet.
- The branch now uses Vercel's URL-based bypass bootstrap in the Playwright
  smoke tests instead of relying only on extra HTTP headers.

## Next Step

Commit and push `feat-preview-bypass-hosted-smoke`, then rerun `Hosted Website
Smoke` against the protected Vercel preview URL from that branch so GitHub
actually executes the URL-bootstrap implementation.
