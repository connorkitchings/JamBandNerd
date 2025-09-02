# GitHub Actions Automation Guide

**JamBandNerd** features comprehensive automation through GitHub Actions with daily pipeline execution and flexible manual triggers.

## Overview

The platform includes two powerful GitHub Actions workflows:

1. **[Daily Pipeline](#daily-pipeline)** - Comprehensive data pipeline automation
2. **[Test Secrets](#test-secrets)** - Verify secret configuration

---

## Daily Pipeline

**File**: `.github/workflows/daily-pipeline.yml`

### Schedule & Triggers

- **Automatic**: Runs daily at **3:00 PM ET (19:00 UTC)**.
- **Manual**: Can be triggered via the GitHub Actions UI (`workflow_dispatch`) with options to:
  - Run for a specific band (`goose`, `phish`, `wsp`) or `all`.
  - Skip the accuracy calculation steps for a faster run.

### Execution Strategy

The workflow uses a **single job** with a **matrix strategy** to run a full pipeline for each band in parallel. This approach is both efficient and resilient.

- **Parallel Jobs**: A separate, parallel job is created for each band (`goose`, `phish`, `wsp`).
- **Resilience**: Since `fail-fast` is set to `false`, a failure in one band's pipeline (e.g., an API is down) will not cancel the jobs for the other bands.
- **Sequential Steps**: Within each band's job, the pipeline steps run sequentially to ensure data dependency is respected:
  1. **Data Collection**: Runs the band-specific collection script (e.g., `run_goose_collection.py`).
  2. **Generate Predictions**: Runs `generate_predictions.py` for both the `notebook` and `ckplus` models.
  3. **Run Backtest**: Runs `run_backtest.py` for both models to populate the `accuracy_per_show` table.
  4. **Calculate Aggregate Accuracy**: Runs `save_aggregate_accuracy.py` for both models to generate the final accuracy summaries.

This design simplifies the workflow's structure, making it easier to read, maintain, and debug compared to previous multi-job designs.

### Environment & Dependencies

#### Python Environment

- **Python Version**: 3.12
- **Package Manager**: UV (auto-installed via curl)
- **Virtual Environment**: `.venv` with project dependencies

#### Required Secrets

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase service role key  
- `PHISH_API_KEY`: Your phish.net API key (optional for Phish data only)

### Error Handling

#### Resilience Features

- **fail-fast: false**: Individual failures don't stop the entire pipeline
- **Matrix Independence**: Each band/model combination runs independently
- **Timeout Protection**: Prevents runaway jobs with reasonable time limits
- **Graceful Degradation**: Pipeline continues with available data when components fail

#### Monitoring & Reporting

- **GitHub Step Summary**: Automated success/failure reporting
- **Detailed Logging**: Comprehensive output with grouped sections
- **Status Tracking**: Per-job status with overall pipeline health

### Manual Usage

#### Trigger Pipeline

1. Go to **Actions** tab in GitHub repository
2. Select **"Daily Data Pipeline"**
3. Click **"Run workflow"**
4. Configure options:
   - **Band**: Select `all`, `goose`, or `phish`
   - **Use optimized pipeline**: Check for experimental single-script mode

#### Monitor Execution

- **Live Logs**: Real-time execution monitoring
- **Step Groups**: Organized logging with collapsible sections
- **Summary Report**: Automated pipeline status summary
- **Error Details**: Comprehensive failure information when issues occur

---

## Test Secrets

**File**: `.github/workflows/test_secrets.yml`

### Purpose

Verify that all required secrets are properly configured in the GitHub repository.

### Usage

1. Go to **Actions** tab
2. Select **"Test Secrets Availability"**
3. Click **"Run workflow"**

### Validation

Checks for presence of:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `PHISH_API_KEY`

---

## Setup Instructions

### 1. Configure Repository Secrets

In your GitHub repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add the following repository secrets:

```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_service_role_key
PHISH_API_KEY=your_phish_net_api_key  # Optional
```

### 2. Enable GitHub Actions

1. Ensure GitHub Actions are enabled in repository settings
2. Workflows will appear under the **Actions** tab
3. The daily pipeline will run automatically at 3 PM ET

### 3. Monitor First Run

1. Trigger a manual run to verify setup
2. Check logs for any configuration issues
3. Verify data appears in your Supabase database
4. Access predictions via the Streamlit web interface

---

## Advanced Configuration

### Custom Scheduling

To modify the daily schedule, edit the cron expression:

```yaml
on:
  schedule:
    - cron: '0 19 * * *'  # 19:00 UTC = 3:00 PM ET (DST)
```

### Band-Specific Execution

For production deployments focusing on specific bands:

1. Modify the matrix strategy in `daily-pipeline.yml`
2. Remove unwanted bands from the collection matrix
3. Update prediction and accuracy matrices accordingly

### Timeout Adjustments

Adjust timeouts based on your data volume:

```yaml
timeout-minutes: 45  # Data collection
timeout-minutes: 20  # Prediction generation  
timeout-minutes: 30  # Accuracy calculation
```

---

## Troubleshooting

### Common Issues

#### Secret Configuration

- **Error**: "Secret not set"
- **Solution**: Verify all required secrets are configured in repository settings

#### API Rate Limits

- **Error**: HTTP 429 errors
- **Solution**: Built-in rate limiting should handle this automatically

#### Timeout Errors

- **Error**: Job exceeds timeout
- **Solution**: Increase timeout values or optimize data collection scope

#### Database Connection

- **Error**: Supabase connection failures
- **Solution**: Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct

### Debugging

#### Enable Debug Logging

Modify scripts to include verbose logging for troubleshooting:

```bash
# Add --debug flag to scripts where available
python scripts/run_goose_collection.py --skip-validation --debug
```

#### Check Pipeline Summary

- Review the automated summary in the Actions tab
- Individual job logs provide detailed error information
- Step groups organize output for easier debugging

---

## Best Practices

### Production Deployment

1. **Test First**: Run manual workflows before relying on daily automation
2. **Monitor Initially**: Check first few automated runs for issues
3. **Scale Gradually**: Start with single bands, expand to full pipeline
4. **Backup Strategy**: Ensure Supabase backups are configured

### Performance Optimization

1. **Skip Validation**: Use `--skip-validation` for faster collection in production
2. **Limit Scope**: Use `--only-setlists` for Phish to focus on recent data
3. **Optimize Frequency**: Adjust daily schedule based on data update patterns

### Security

1. **Secret Management**: Use GitHub repository secrets, never hardcode credentials
2. **Access Control**: Limit who can modify workflows and secrets
3. **Audit Logs**: Regularly review GitHub Actions execution logs

---

## Integration with Web Interface

The automated pipeline feeds directly into the Streamlit web interface:

1. **Data Collection** → Raw Supabase tables (`{band}_*_raw`)
2. **Predictions** → Unified tables (`predictions_notebook`, `predictions_ckplus`)
3. **Accuracy** → Summary tables (`notebook_accuracy`, `accuracy_ckplus`)
4. **Web Interface** → Real-time display of latest predictions and accuracy metrics

This creates a complete automated workflow from data collection to user-facing predictions, updating daily without manual intervention.
