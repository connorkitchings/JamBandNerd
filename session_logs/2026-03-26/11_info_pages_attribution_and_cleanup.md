# Session 11: Info Pages Attribution And Cleanup

**Date:** 2026-03-26  
**Goal:** Improve About, Data Use, and Contact for usability, tighten model attribution, and harden public-facing source wording.

## Constraints
- Credit Notebook as based on the method developed by Phish.net
- Identify CK+ as a personally developed model
- Remove the redundant supported-bands section from About
- Remove stale GitHub references now that the site no longer links there
- Avoid naming individual data providers in public-facing source explanations
- Keep wording careful and good-faith rather than overly legalistic or provocative

## Commands Run
```bash
npm run lint:web
npm run build:web
```

## Files Changed
- `apps/web/src/app/about/page.tsx` - Removed the supported-bands section; removed redundant eyebrow labels and the `Model lineage` block; updated FAQ copy; removed GitHub references; preserved line breaks in the model explanation; and aligned Notebook attribution plus source-language wording
- `apps/web/src/app/data-use/page.tsx` - Added and refined source-attribution and model-credit language, clarified the factual-data framing, and softened source wording to avoid naming providers directly
- `apps/web/src/app/contact/page.tsx` - Tightened the email section and overall contact-page hierarchy

## Validation Status
- `npm run lint:web`: passed
- `npm run build:web`: passed
- Later follow-up edits after validation were copy-only on About and Data Use

## Next Step
Keep informational-page copy tight and consistent with the current product language if additional public-policy text is added later.
