# Agent Playbook

This file stores persistent lessons and operating patterns that should survive across sessions.

## Rules

1. Treat `README.md` and `docs/user/pipeline_usage.md` as the command source of truth.
2. Preserve the `reference_date` anti-leakage boundary in any transformation or modeling change.
3. Keep shared pipeline code band-agnostic; push source-specific behavior into collectors.
4. Prefer consolidated scripts in `scripts/` before reaching for historical or manual utilities.
5. If you change agent workflows, update `.agent/`, `README.md`, and relevant contributor docs together.

## Strategies

1. Use a small boot order and fetch docs on demand to avoid context bloat.
2. Treat `docs/logs/` as archive/history and `session_logs/` as the active session system.
3. Keep quality gates explicit and copy-pasteable so every AI tool uses the same validation path.

## Success Patterns

- Start from `.agent/CONTEXT.md`, not from broad repo search.
- Use `scripts/README.md` when reconciling which scripts are canonical vs manual/admin.
- When guidance drifts, fix the root entrypoints first and update downstream docs second.
- For freshness or orphan checks, validate only completed shows; including today or future scheduled shows creates false positives that look like ingestion failures.
- When performing database read operations for large batch verifications (e.g. checking which setlists are already ingested), always use paginated `fetch_table` wrappers instead of raw Supabase `.execute()` limits which silently truncate after 1000 rows.
- Ensure API endpoints queried by collectors include trailing slashes if the server is known to redirect to internal ports that may be unreachable.
- For live pytest suites that gate on `os.environ`, export `.env` into the shell before invoking `pytest`; app-level `load_dotenv()` hooks do not help preflight env checks that run first.
- For `uv` projects, audit the exported lockfile with `uv export --no-emit-project` plus `pip-audit`; `uvx pip-audit` on its own audits the tool environment, not the repo dependency set.
- Keep pipeline and website Supabase credentials separate: scripts should use `SUPABASE_SERVICE_ROLE_KEY`, while the website should use `SUPABASE_ANON_KEY` and reject `sb_secret_` keys.
- In typed Next.js apps using Supabase JS, dynamic `.select()` column strings often confuse the generated parser types; prefer `select("*")` plus explicit record narrowing when the column names are runtime-driven.
- When integrating Google Stitch exports into the Next.js app, treat Stitch as visual input only: convert exports into typed components, keep data fetching server-side, and replace placeholder bands/models/routes with real repo-supported values before shipping.
- For npm workspace smoke checks, do not rely on `npm run <script> -- --list` forwarding through multiple script layers; add an explicit `:list` script so CI and local verification use the same command path.
- Before retiring a legacy codebase (e.g. Streamlit app), delete its corresponding tests first so pytest doesn't fail during collection. Run `pytest` immediately after deletion to catch any remaining import references before committing.
- When running a Next.js workspace (e.g. `npm run dev:web`) from the repository root, ensure the `.env.local` file is placed inside the workspace directory (`apps/web/.env.local`), not at the repository root, so that Next.js automatically loads it.
- For Vercel monorepo deployments, set the project root to the actual Next.js workspace (here `apps/web`) or Vercel will build from the repo root and fail with “Couldn't find any `pages` or `app` directory.”
- For Playwright smoke tests on pull requests, assume runtime secrets may be unavailable. Keep route coverage intact by accepting the app's explicit missing-env fallback state for secret-backed pages instead of requiring live Supabase data in PR CI.
- When moving a Next.js dashboard off `/` onto a dedicated route like `/predictions`, keep old root query links working with a compatibility redirect and update shared nav/link builders in the same pass; otherwise stale `/?band=...` links linger across the site.
- When backfilling a “last N replayable shows” product surface, do not rebuild exactly `N` completed shows. Use a buffered window (for example, `75` to guarantee `50`) because sparse recent shows may be intentionally skipped during scoring, and validate replay lineage per `show_date` rather than per raw accuracy row when duplicates can coexist.
- In `session_logs/`, restart numbering at `01` for each date directory. If a session ends up with several tiny follow-up entries that belong to the same content thread, prefer consolidating them into the earlier log instead of stacking redundant near-duplicate logs.

- When hardening data ingestion, add HTTP response caching at the collector base class level (not per-band) with configurable TTL via env vars. Use a circuit breaker pattern to disable failing bands after N consecutive failures.
- ID column naming inconsistency (e.g., show_id vs api_show_id vs source_uuid) should be addressed via a formal migration strategy, not ad-hoc changes, since it affects the entire data pipeline.
- Keep band-specific exclusion filters (like WSP jam/drums) in a centralized config (config/bands.py) rather than hardcoded in model files.
- When prediction storage needs song-level SQL access, keep the run-level JSON tables as the canonical write path and add a rebuildable per-song projection; otherwise reruns with smaller `top_k` values will leave stale projected rows unless the projection is deleted and rewritten per `(band, reference_date, model_version)`.
- For destructive recovery paths, clear derived outputs just-in-time per band/model and validate both predictions and accuracy after rebuild; this avoids wiping every downstream table up front when a later network or backtest step fails.
- In WSP audits, classify recent missing setlists before failing the band: treat upstream Everyday Companion pages without a setlist table as warnings, and reserve hard failures for collector-visible pages, request failures without fallback, or missing source metadata.
- For dynamic Supabase-backed configuration on the website (e.g. bands, models), thread fetched data as props through component layers rather than making per-component Supabase calls. A layout-level fetch + prop drilling avoids waterfall fetches while keeping the data layer server-side. Use a typed `RouteState` union (`ready | missing_env | error | empty`) consistently so every fetcher has the same error handling contract.
- When migrating hardcoded config to database-backed config in a Next.js app, keep the old config as a static fallback: if Supabase is unavailable (local dev, CI, edge), fall back to the static values so the app degrades gracefully without breaking.
- When implementing real-time features in Next.js Server Components with Supabase, use a small client-side wrapper component that listens to Supabase Realtime `postgres_changes` and gracefully calls `router.refresh()`. This silently rebuilds the server components without hydration mismatches or jarring full page reloads.
- In the website app, remove unused client islands instead of keeping “maybe later” UI code around, and scope any realtime listener to the active route keys (for example `band`, `model`, and `reference_date`) before calling `router.refresh()`. Broad subscriptions create unnecessary refresh churn and make performance issues harder to reason about.
- When integrating open social platforms like Bluesky for public data scraping, utilize the public AT Protocol endpoints (e.g., `app.bsky.feed.getAuthorFeed`) for keyless, auth-free public post retrieval instead of building a heavy scraper.
- To eliminate awkward gaps in data tables on wide screens, avoid `table-fixed` with empty columns. Instead, use a full-width container and align metric columns (numbers, dates) to the right (`text-right`). This anchors the identifiers (songs, names) to the left and metrics to the right, making any empty space in the middle feel like natural breathing room rather than a layout bug.
- Ensure top-level navigation and control bars (e.g., band/model selectors) are unified across routes. Use a consistent grid or flex layout for selectors so they form predictable blocks, and vertically center labels (e.g., "Band:", "Model:") alongside their button groups to maintain a professional, dashboard-grade feel.
- For user-facing model evaluation dashboards, prioritize **Precision (Hit Rate)** over academic Recall. While Recall is technically more robust for coverage, users intuitively expect "Hits / Predictions" (e.g., 2/10 = 20%). When both are needed, stack them vertically with Recall as the primary bold metric and Precision as a smaller secondary "Prec" or "Hit Rate" label to maintain trust without sacrificing clarity.
- When adding HTTP User-Agent identity to data collectors across multiple bands, centralize the constant in `config.py` and reference it from each collector. Use a descriptive format like `JamBandNerd-Bot/1.0 (+https://jambandnerd.com/data-use)` that includes contact info and policy link for server admins to understand the requester's intent.
