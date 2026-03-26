# Session Log: 2026-03-25 - Predictions Selector Box Reorganization

## Goal

Reorganize the predictions-page selector box so band switching remains the primary action, model controls stay grouped together, and the compare action lives inside the model section with cleaner alignment.

## Constraints

- Preserve the existing predictions route, query params, and band/model selection behavior
- Keep the change limited to UI structure and presentation
- Work within the broader editorial design system already applied across `apps/web`

## Commands run

- `npm run lint:web`
- `npm run build:web`
- `npm run start --workspace @jambandnerd/web -- --hostname 127.0.0.1 --port 3101`
- `npx playwright screenshot --device="Desktop Chrome" --full-page --wait-for-timeout 1500 http://127.0.0.1:3101/predictions /tmp/jbn-predictions-selector-box-v1.png`

## Files changed

- `apps/web/src/components/dashboard-side-nav.tsx`

## Validation status

- `npm run lint:web`: passed
- `npm run build:web`: passed
- Browser check:
  - band and model selectors now read as separate control groups
  - band section has more visual weight than the model section
  - model buttons remain on the first row with `Compare Models` directly beneath inside the same group
  - selector labels were later simplified to centered `Band` and `Model` labels without helper copy

## Next step

Continue the same page-specific pass on `/predictions`, focusing on the remaining hero and board details now that the main selector surface is organized.
