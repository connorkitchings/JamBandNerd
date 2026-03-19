# JamBandNerd Documentation

Welcome to the comprehensive documentation for JamBandNerd, a cloud-based data platform for collecting, transforming, and predicting jam band setlists.

This documentation is organized into audience-focused sections:

### 🚀 [User Guide](user/getting_started.md)
- **[Getting Started](user/getting_started.md)**: Environment setup and installation.
- **[Pipeline Usage](user/pipeline_usage.md)**: Running the collection and prediction workflows.
- **[Configuration](user/configuration.md)**: Band and model configuration options.

### 🧑‍💻 [Contributor Guide](contributor/onboarding.md)
- **[Onboarding](contributor/onboarding.md)**: How to get oriented and make your first contribution.
- **[Architecture](contributor/developer_guide/architecture.md)**: System design and component overview.
- **[Extending the Platform](contributor/developer_guide/extending_the_platform.md)**: Patterns for new bands and models.
- **[Agentic Development](contributor/developer_guide/ai_sessions.md)**: Canonical AI entrypoints, startup flow, and session logging workflow.

### ⚙️ [Operations](operations/github_actions.md)
- **[Daily Pipeline](operations/github_actions.md)**: GitHub Actions workflow and monitoring notes.
- **[Pipeline Optimization](operations/pipeline_optimization.md)**: Consolidation strategy and performance tips.
- **[Website Delivery Strategy](operations/website_delivery.md)**: Website-first architecture, deployment target, and migration path.
- **[Legacy Streamlit Interface](operations/streamlit_deploy.md)**: Temporary local validation surface during the website migration.
- **[TourWrangler Fallback](operations/tourwrangler_fallback.md)**: Backup ingestion runbook for WSP.

### 📚 Reference Library
- **Specs**: [Technical Overview](reference/specifications/technical_overview.md) · [CLI](reference/specifications/cli.md) · [Transformations](reference/specifications/transformations.md).
- **Schemas**: [Unified Tables](reference/schemas/unified_tables.md) · [Goose API](reference/schemas/goose_api.md) · [Phish API](reference/schemas/phish_api.md) · [WSP Webscrape](reference/schemas/wsp_webscrape.md) · [UM AllThings](reference/schemas/um_allthings.md).
- **Models**: [Model Overview](reference/models/index.md) plus detailed pages for the [Notebook](reference/models/notebook.md) and [CK+](reference/models/ckplus.md) predictors.
- **Supabase Helpers**: [API Guide](reference/guides/supabase_api_guide.md) and [Insert Recipes](reference/guides/supabase_inserts.md).

### 📊 Project Overview
- **Status Dashboard**: [Implementation Status](overview/implementation_status.md).
- **Product Docs**: [PRD](overview/project/prd.md) · [Architecture Decisions](overview/project/adr.md) · [Schedule](overview/project/schedule.md).

### 🛠️ Troubleshooting & Reports
- **Guides**: [Data Ingestion & Streamlit Issues](troubleshooting/data_ingestion_and_streamlit_issues.md) · [Validation Fix Log](troubleshooting/VALIDATION_FIX_2025-10-04.md) · [Data Quality Checklist](troubleshooting/troubleshooting_data_quality.md).
- **Reports**: [Improvements Summary](reports/IMPROVEMENTS_SUMMARY.md) · [Validation Improvements](reports/VALIDATION_IMPROVEMENTS.md) · [Validation Test Report](reports/TEST_REPORT_VALIDATION.md).
