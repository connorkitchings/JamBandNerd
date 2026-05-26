# Operations Docs

Active runbooks for operating the JamBandNerd pipeline and website.

## Active

| File | Purpose |
|------|---------|
| [github_actions.md](github_actions.md) | All GitHub Actions workflows — schedule, triggers, failure policy |
| [website_delivery.md](website_delivery.md) | Website delivery strategy, Vercel setup, env vars, release versioning |
| [main_branch_elevation.md](main_branch_elevation.md) | Production gate for `main` — PR policy, required checks, release flow |
| [tourwrangler_fallback.md](tourwrangler_fallback.md) | WSP TourWrangler fallback when EverydayCompanion is unavailable |
| [streamlit_deploy.md](streamlit_deploy.md) | Historical landing page for Streamlit references (retired product surface) |

## Archive

Pre-launch and one-time operational documents are in [`docs/archive/`](../archive/).

| File | What it was |
|------|------------|
| `v1_punch_list.md` | Pre-launch v1.0 punch list (complete as of 2026-05-23) |
| `frontend_strategy.md` | Frontend migration design doc (absorbed into `website_delivery.md` and `architecture.md`) |
| `test_results_2025-12-01.md` | Point-in-time test results from Dec 2025 |
| `pipeline_optimization.md` | Pipeline optimization notes from early development |
| `repo_hygiene_audit.md` | One-time hygiene audit (complete) |
| `mobile_verification.md` | Pre-launch mobile review notes |
| `wsp_403_fix.md` | WSP 403 incident post-mortem |
| `data_recovery_rebuild.md` | One-time data recovery event |
