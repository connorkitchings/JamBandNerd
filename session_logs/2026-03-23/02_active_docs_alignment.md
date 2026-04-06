# 2026-03-23 Session Log 02

## Goal

Align active documentation with the repo's current website-first state so top-level contributor and user docs no longer describe the website as a migration target or Streamlit as an active fallback path.

## Constraints

- Limit the sweep to active docs and active navigation surfaces.
- Preserve legacy/historical troubleshooting content where it still has archival value.
- Avoid code, schema, or workflow changes in this session.

## Commands Run

```bash
git checkout -b docs-active-state-alignment
rg -n "migration in progress|legacy transition surface|final cutover|cut over|Streamlit fallback|remains a legacy transition surface|target public surface|retired only|remaining website work" README.md docs
uv run --with mkdocs --with mkdocs-material --with pymdown-extensions mkdocs build
git diff --check
```

## Files And Artifacts

- `README.md`
- `docs/user/pipeline_usage.md`
- `docs/index.md`
- `docs/overview/implementation_status.md`
- `docs/operations/website_delivery.md`
- `docs/operations/streamlit_deploy.md`
- `docs/contributor/developer_guide/architecture.md`
- `docs/reference/specifications/technical_overview.md`
- `session_logs/2026-03-23/02_active_docs_alignment.md`

## Validation

- Targeted stale-language search across README and docs returned no remaining matches for the retired migration/fallback phrases in active docs.
- `mkdocs build` succeeded.
- `git diff --check` passed after removing one trailing-space issue in `docs/overview/implementation_status.md`.
- `mkdocs build` still reports a pre-existing warning in `operations/frontend_strategy.md` for a bad relative link to `reference/specifications/data_strategy.md`.

## Next Step

Decide whether to keep the remaining legacy Streamlit docs as-is for historical debugging, or reduce their prominence further now that the active docs consistently treat the website as the sole product surface.
