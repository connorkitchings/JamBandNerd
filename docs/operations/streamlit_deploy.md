# Legacy Streamlit Interface Guide

This guide covers the legacy Streamlit interface that remains in the repo as a temporary internal
fallback. It is not the primary local workflow and it is no longer part of the recommended public
deployment path for JamBandNerd.

For the current product direction, see [Website Delivery Strategy](website_delivery.md).

## Legacy fallback only

```bash
uv venv --python=3.12
source .venv/bin/activate
uv pip install .
streamlit run src/jambandnerd/web/app.py
```

Use this only when you need to compare legacy behavior against the website during cutover. The default frontend workflow lives in `apps/web`.

For local secrets, create `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR_KEY"
PHISH_API_KEY = "optional"
```

## Legacy Status

- The public product surface is the website.
- The Streamlit app remains useful only for temporary fallback validation.
- New frontend product work should target `apps/web` unless a legacy validation gap requires a short-lived Streamlit change.

## Historical Streamlit Cloud Notes

1. Connect your GitHub repo and choose the app entry point:
   - App file: `src/jambandnerd/web/app.py`
   - Python: 3.12 (declare in `pyproject.toml` via `requires-python` or provide a `runtime.txt` with `3.12`)
2. Add secrets in the app Settings → Secrets:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `PHISH_API_KEY` (only if needed)
3. (Optional) Keep a `requirements.txt` for broad compatibility if the resolver struggles with your `pyproject.toml`.
4. Deploy only if you explicitly need the historical fallback path. Cloud logs are available under the app’s Logs tab.

Important: GitHub Actions secrets do not automatically become runtime secrets in Streamlit Cloud.
Add runtime secrets in the Streamlit app’s Secrets panel. The app prefers `st.secrets` and falls
back to environment variables.

## App configuration (.streamlit/config.toml)

This repo includes `.streamlit/config.toml` to standardize server options and theming. Cloud honors these settings.

```toml
[server]
headless = true
address = "0.0.0.0"
port = 8501
enableCORS = false
enableXsrfProtection = true

[theme]
base = "light"
primaryColor = "#1f77b4"
```

## Secrets resolution in code

`src/jambandnerd/db/connection.py` now prefers Streamlit secrets, with environment variable fallback. When running on Streamlit Cloud, set credentials in the Secrets panel. Locally, use `.env` or `.streamlit/secrets.toml`.

## Performance and caching

- The Supabase client is cached using `st.cache_resource` (`supabase_client_cached()`), reducing connection overhead.
- Data fetches use `st.cache_data` with short TTLs for freshness.

## Shareable URLs (deep links)

The app syncs selections to query parameters. You can link to a specific view:

- `?band=goose&model=notebook&k=50`
- `?band=eggy&model=ckplus&k=25`
- `?band=phish&model=ckplus&k=25`
- `?band=billy&model=notebook&k=10`

Unsupported values gracefully fall back to defaults.

## Optional password gate

You can add an `APP_PASSWORD` secret to require a simple password gate. See `app.py` for the example guard function (commented example in the docs/answers). Set `APP_PASSWORD` in Streamlit Secrets to enable.

## Troubleshooting

- Auth/credentials: Ensure `SUPABASE_URL` and `SUPABASE_KEY` are present in the app’s Secrets panel.
- Dependency issues: Provide a `requirements.txt` that includes `streamlit`, `pandas`, `altair`, `supabase`, and optionally `-e .`.
- Logs: Use the app’s Logs page for errors and tracebacks.
- Path prefix/proxy: If hosting behind a custom proxy, set `baseUrlPath` in `.streamlit/config.toml` and adjust your reverse proxy accordingly.

## Historical CI/CD behavior

Streamlit Cloud redeploys automatically on pushes to the configured branch. For reproducibility, pin key dependencies in `pyproject.toml` or `requirements.txt` as needed.
