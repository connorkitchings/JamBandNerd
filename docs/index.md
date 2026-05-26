# JamBandNerd Documentation

Welcome to the comprehensive documentation for JamBandNerd — a data platform for collecting, transforming, and predicting jam band setlists. Live at [jambandnerd.com](https://jambandnerd.com) (v1.0.1).

This documentation is organized into current operating docs first, then historical context.

## Current Canonical Docs

### 🚀 [User Guide](user/getting_started.md)
- **[Getting Started](user/getting_started.md)**: Environment setup and installation.
- **[Pipeline Usage](user/pipeline_usage.md)**: Running the collection and prediction workflows.
- **[Configuration](user/configuration.md)**: Runtime and model configuration surfaces.

### 🧑‍💻 [Contributor Guide](contributor/onboarding.md)
- **[Onboarding](contributor/onboarding.md)**: How to get oriented and make your first contribution.
- **[Architecture](contributor/developer_guide/architecture.md)**: System design and component overview.
- **[Extending the Platform](contributor/developer_guide/extending_the_platform.md)**: Patterns for new bands and models.
- **[Agentic Development](contributor/developer_guide/ai_sessions.md)**: Canonical AI entrypoints, startup flow, and session logging workflow.
- **[Model Development](contributor/model_development.md)**: Adding and promoting per-band prediction models.

### ⚙️ [Operations](operations/README.md)
- **[Operations Index](operations/README.md)**: Full list of active runbooks and archived ops docs.
- **[GitHub Actions](operations/github_actions.md)**: All workflows — schedule, triggers, failure policy.
- **[Website Delivery](operations/website_delivery.md)**: Website architecture, Vercel setup, env vars, versioning.
- **[Main Branch Elevation](operations/main_branch_elevation.md)**: Production gate — PR policy, required checks, release flow.
- **[WSP Fallback](operations/tourwrangler_fallback.md)**: TourWrangler fallback runbook for WSP.

### 📚 Reference Library
- **Specs**: [Data Strategy](reference/specifications/data_strategy.md) · [CLI](reference/specifications/cli.md) · [Transformations](reference/specifications/transformations.md) · [Database](reference/specifications/database.md) · [Predictions Schema](reference/specifications/predictions_schema.md).
- **Schemas**: [Unified Tables](reference/schemas/unified_tables.md) · [Goose API](reference/schemas/goose_api.md) · [Phish API](reference/schemas/phish_api.md) · [WSP Webscrape](reference/schemas/wsp_webscrape.md) · [UM AllThings](reference/schemas/um_allthings.md).
- **Supabase Helpers**: [API Guide](reference/guides/supabase_api_guide.md) and [Insert Recipes](reference/guides/supabase_inserts.md).

### 📊 Reports
- **Reports**: [Alignment Audit](reports/2026-04-13_alignment_audit.md) · [Improvements Summary](reports/IMPROVEMENTS_SUMMARY.md) · [Validation Improvements](reports/VALIDATION_IMPROVEMENTS.md) · [Validation Test Report](reports/TEST_REPORT_VALIDATION.md).

## Historical And Legacy Context

- **Historical model reference**: [CK+ Model](reference/models/ckplus.md)
- **Historical product/architecture snapshots**: [Technical Overview](reference/specifications/technical_overview.md) · [ADR](overview/project/adr.md) · [Schedule](overview/project/schedule.md)
- **Historical Streamlit note**: [Streamlit Notes](operations/streamlit_deploy.md)
- **Pre-launch operations archive**: `docs/archive/` — v1 punch list, frontend strategy, test results, and other one-time operational artifacts.
- **Troubleshooting archive**: [Data Quality Checklist](troubleshooting/troubleshooting_data_quality.md) plus targeted historical fixes in `docs/troubleshooting/`
