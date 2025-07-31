# JamBandNerd Automation

This directory contains automation scripts and configuration for running the JamBandNerd data
collection and prediction pipelines on a scheduled basis.

## Overview

The automation system is designed to run daily at **3:00 PM Eastern Time** and consists of two main stages:

1. **Data Collection**: Updates WSP data in Supabase (Phish and Goose use real-time APIs)
2. **Predictions**: Generates fresh predictions for all bands using both CK+ and Notebook models

## Files

### GitHub Actions Workflow

- **`.github/workflows/daily-pipeline.yml`**: GitHub Actions workflow that runs automatically at
    3 PM ET
  - Handles environment setup and secret management
  - Runs data collection followed by predictions
  - Uploads logs as artifacts for debugging

### Automation Scripts

- **`automation/daily_pipeline.py`**: Main orchestrator script for daily pipeline execution
  - Can be run locally or in automated environments
  - Supports data-only, predictions-only, and verbose modes
  - Generates comprehensive logging and summary reports

### Configuration Files

- **`automation/requirements.txt`**: Python dependencies for automation environment
- **`automation/docker-compose.yml`**: Docker setup for containerized execution (optional)
- **`automation/cron-setup.sh`**: Shell script for setting up cron jobs on Unix systems

## GitHub Secrets Required

For the GitHub Actions workflow to function, you need to set these repository secrets:

```
PHISH_API_KEY=your_phish_net_api_key
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

## Usage

### GitHub Actions (Recommended)

The workflow runs automatically at 3 PM ET daily. You can also trigger it manually:

1. Go to the "Actions" tab in your GitHub repository
2. Select "Daily JamBandNerd Pipeline"
3. Click "Run workflow"

### Local Execution

```bash
# Run complete pipeline
python automation/daily_pipeline.py

# Run only data collection
python automation/daily_pipeline.py --data-only

# Run only predictions
python automation/daily_pipeline.py --predictions-only

# Enable verbose logging
python automation/daily_pipeline.py --verbose
```

### Cron Setup (Unix/Linux)

```bash
# Make the cron setup script executable
chmod +x automation/cron-setup.sh

# Run the setup script
./automation/cron-setup.sh
```

## Pipeline Architecture

### Data Collection Stage

- **WSP**: Scrapes and updates Supabase with latest show/setlist data
- **Phish/Goose**: No separate collection needed (APIs provide real-time data)

### Prediction Stage

- **All Bands**: Generate predictions using:
  - CK+ Model: Gap-based predictions with statistical analysis
  - Notebook Model: Frequency-based predictions with recent show filtering
- **Output**: Unified prediction tables in Supabase (`predictions_ckplus`, `predictions_notebook`)

## Monitoring and Logs

### GitHub Actions

- Logs are available in the Actions tab of your repository
- Artifacts are uploaded for both collection and prediction logs
- Email notifications can be configured for failures

### Local Execution

- Logs are written to `logs/automation/daily_pipeline_YYYYMMDD.log`
- Console output provides real-time status updates
- Summary reports show overall execution status

## Troubleshooting

### Common Issues

1. **API Rate Limits**: If you encounter rate limiting, the scripts include retry logic
2. **Supabase Connection**: Verify your SUPABASE_URL and SUPABASE_KEY are correct
3. **Missing Dependencies**: Run `pip install -e .` from the project root

### Debug Mode

Run with `--verbose` flag for detailed debugging information:

```bash
python automation/daily_pipeline.py --verbose
```

### Manual Testing

Test individual components:

```bash
# Test WSP data collection
python -m jambandnerd.data_collection.wsp.run_pipeline_supabase

# Test all predictions
python -m jambandnerd.predictions.run_all_predictions

# Test specific band predictions
python -m jambandnerd.predictions.phish.ckplus_pipeline
```

## Customization

### Scheduling

To change the execution time, modify the cron expression in `.github/workflows/daily-pipeline.yml`:

```yaml
schedule:
  - cron: '0 20 * * *'  # 3 PM ET (20:00 UTC during DST)
```

### Pipeline Configuration

Band-specific settings can be modified in:

- `src/jambandnerd/predictions/[band]/data_transformer.py`
- Model parameters in `src/jambandnerd/models/`

## Support

For issues with the automation system:

1. Check the logs in GitHub Actions or local log files
2. Verify all required secrets/environment variables are set
3. Test individual pipeline components manually
4. Review the troubleshooting section above
