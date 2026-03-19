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
- In typed Next.js apps using Supabase JS, dynamic `.select()` column strings often confuse the generated parser types; prefer `select("*")` plus explicit record narrowing when the column names are runtime-driven.
- When integrating Google Stitch exports into the Next.js app, treat Stitch as visual input only: convert exports into typed components, keep data fetching server-side, and replace placeholder bands/models/routes with real repo-supported values before shipping.
- For npm workspace smoke checks, do not rely on `npm run <script> -- --list` forwarding through multiple script layers; add an explicit `:list` script so CI and local verification use the same command path.
- Before retiring a legacy codebase (e.g. Streamlit app), delete its corresponding tests first so pytest doesn't fail during collection. Run `pytest` immediately after deletion to catch any remaining import references before committing.
- When running a Next.js workspace (e.g. `npm run dev:web`) from the repository root, ensure the `.env.local` file is placed inside the workspace directory (`apps/web/.env.local`), not at the repository root, so that Next.js automatically loads it.
