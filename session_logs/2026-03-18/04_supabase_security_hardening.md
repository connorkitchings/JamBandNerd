# Supabase Security Hardening

## Goal

- Upgrade the Supabase Python stack and add durable dependency monitoring after reviewing current vulnerability posture.

## Constraints

- Keep the dependency audit separate from `daily-pipeline.yml` so data ingestion and publishing are not blocked by package findings.
- Use the `uv` lockfile as the source of truth rather than introducing a parallel dependency-management path.
- Resolve any currently auditable dependency findings before adding a failing scheduled audit workflow.

## Commands Run

```bash
uv tree | rg "supabase|postgrest|realtime|storage3|supabase-auth|supabase-functions|httpx|websockets"
uv lock --upgrade-package supabase
uv lock --upgrade-package h2 --upgrade-package pillow --upgrade-package protobuf --upgrade-package pyjwt --upgrade-package tornado --upgrade-package urllib3
uv lock --upgrade-package streamlit --upgrade-package pillow

tmpfile=$(mktemp /tmp/jbn-audit.XXXXXX)
uv export --format requirements-txt --locked --no-hashes --no-emit-project --output-file "$tmpfile"
uv run --with pip-audit python -m pip_audit -r "$tmpfile" --cache-dir /tmp/pip-audit-cache --no-deps --disable-pip
```

## Files Changed

- `uv.lock`: upgraded the Supabase family to `2.28.2` and refreshed vulnerable transitive packages.
- `.github/dependabot.yml`: added weekly Dependabot coverage for `uv` and GitHub Actions.
- `.github/workflows/dependency-audit.yml`: added a standalone scheduled/manual lockfile audit workflow.
- `README.md`: documented the new dependency maintenance path.

## Validation Status

- The Supabase family upgraded cleanly to `2.28.2`.
- Follow-up lockfile tightening upgraded `h2`, `protobuf`, `pyjwt`, `tornado`, `urllib3`, `streamlit`, and `pillow`.
- Local audit command shape was validated against the exported `uv` lockfile and is suitable for the new GitHub Actions workflow.

## Notes

- The original `uvx pip-audit` approach was discarded because it audits the tool environment rather than this project.
- The audit workflow intentionally remains separate from `daily-pipeline.yml` so dependency findings do not interrupt ingestion, prediction, or publishing jobs.

## Next Step

- Commit and push the dependency hardening changes, then manually dispatch `Dependency Audit` once to confirm the remote workflow passes under GitHub Actions.
