# Session Log: 2026-03-25 - Predictions Precision Cards Swap

## Goal

Replace the predictions hero's board-shape metric cards with historical precision metrics for the selected band/model so the page gives a clearer sense of prediction trustworthiness.

## Constraints

- Keep the predictions page functional even if recent accuracy data is unavailable
- Avoid route, schema, or API changes
- Preserve the existing `Show Outlook` card and hero layout

## Commands run

- `npm run lint:web`
- `npm run build:web`
- `npm run start --workspace @jambandnerd/web -- --hostname 127.0.0.1 --port 3104`
- `node -e 'const { chromium } = require("playwright"); ...'`

## Files changed

- `apps/web/src/app/predictions/page.tsx`
- `apps/web/src/components/prediction-hero.tsx`

## Validation status

- `npm run lint:web`: passed
- `npm run build:web`: passed
- Browser check:
  - hero now shows `Top 10 Precision`, `Top 25 Precision`, and `Top 50 Precision`
  - metrics reflect recent averages for the selected band/model
  - `Show Outlook` popover still opens and remains readable

## Next step

Continue the page-by-page predictions pass and decide whether the precision card sublabels should stay as recent-average framing or be shortened further.
