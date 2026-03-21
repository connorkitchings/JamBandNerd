# Streamlit Deployment

The Streamlit app is a legacy fallback surface retained during the website
cutover. It is no longer the primary public product path.

## Current Status

- preferred public surface: `apps/web`
- Streamlit remains available for internal fallback and comparison only
- new feature work should target the website unless there is a specific fallback
  need

## Local Run

Run the website first when possible:

```bash
npm install
npm run dev:web
```

Use the Streamlit app only when you specifically need the legacy surface for
debugging or fallback validation.

## Guidance

- do not treat Streamlit as the canonical product architecture
- do not add Streamlit-only data contracts
- keep Streamlit compatible with the existing Supabase prediction and accuracy
  tables while the cutover remains incomplete

For the active product direction, see
[Website Delivery Strategy](website_delivery.md).
