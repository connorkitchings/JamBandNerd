# Streamlit Deployment

The Streamlit app is a legacy internal surface retained for debugging and
historical comparison only. It is no longer part of the active product path.

## Current Status

- preferred public surface: `apps/web`
- Streamlit remains available for internal legacy/debugging use only
- new feature work should target the website unless there is a specific legacy
  need

## Local Run

Run the website first when possible:

```bash
npm install
npm run dev:web
```

Use the Streamlit app only when you specifically need the legacy surface for
debugging or historical comparison.

## Guidance

- do not treat Streamlit as the canonical product architecture
- do not add Streamlit-only data contracts
- keep Streamlit compatible with the existing Supabase prediction and accuracy
  tables only as long as the legacy surface remains in the repo

For the active product direction, see
[Website Delivery Strategy](website_delivery.md).
