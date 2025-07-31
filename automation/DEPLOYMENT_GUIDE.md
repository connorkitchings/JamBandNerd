# JamBandNerd Automation Deployment Guide

## 🚀 Quick Start for GitHub Actions

### Step 1: Set Up Repository Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add:

```
PHISH_API_KEY=your_phish_net_api_key_here
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_KEY=your_supabase_anon_key_here
```

### Step 2: Commit and Push

```bash
git add .
git commit -m "Add daily pipeline automation system"
git push origin main
```

### Step 3: Verify Workflow

1. Go to the **Actions** tab in your GitHub repository
2. You should see "Daily JamBandNerd Pipeline" workflow
3. The workflow will run automatically at 3 PM ET daily
4. You can also trigger it manually by clicking "Run workflow"

## 📋 Pre-Deployment Checklist

- [ ] All pipeline tests passed locally
- [ ] GitHub secrets configured correctly
- [ ] `.env` file contains all required variables (for local testing)
- [ ] Supabase tables are properly set up and accessible
- [ ] Repository has been pushed to GitHub

## 🔍 Verification Steps

### Test the Workflow Manually

1. Go to GitHub Actions tab
2. Select "Daily JamBandNerd Pipeline"
3. Click "Run workflow" > "Run workflow"
4. Monitor the execution logs

### Expected Results

- **Data Collection**: WSP data updated in Supabase
- **Predictions**: 6 pipelines generate predictions:
  - Phish CK+ (~100 predictions)
  - Phish Notebook (~123 predictions)
  - Goose CK+ (~100 predictions)
  - Goose Notebook (~91 predictions)
  - WSP CK+ (~100 predictions)
  - WSP Notebook (~51 predictions)

### Success Indicators

- ✅ All jobs complete without errors
- ✅ Prediction counts match expected ranges
- ✅ Supabase tables updated with today's date
- ✅ Log artifacts uploaded successfully

## 🛠️ Troubleshooting

### Common Issues

**1. Secret Configuration Errors**

```
Error: Environment variable PHISH_API_KEY not found
```

**Solution**: Verify all three secrets are set correctly in GitHub repository settings.

**2. Supabase Connection Issues**

```
Error: Failed to create Supabase client
```

**Solution**: Check SUPABASE_URL and SUPABASE_KEY are valid and have proper permissions.

**3. API Rate Limiting**

```
Error: Too many requests to Phish.net API
```

**Solution**: The scripts include retry logic. This usually resolves automatically.

### Debug Mode

Enable verbose logging by modifying the workflow file:

```yaml
- name: Run All Prediction Pipelines
  run: |
    python automation/daily_pipeline.py --verbose
```

### Manual Testing

Test components individually:

```bash
# Test automation script locally
python automation/daily_pipeline.py --predictions-only

# Test individual pipelines
python -m jambandnerd.predictions.run_all_predictions

# Test WSP data collection
python -m jambandnerd.data_collection.wsp.run_pipeline_supabase
```

## 📊 Monitoring

### GitHub Actions Dashboard

- View execution history in Actions tab
- Download log artifacts for detailed debugging
- Set up email notifications for failures

### Log Files

- **GitHub**: Artifacts uploaded after each run
- **Local**: `logs/automation/daily_pipeline_YYYYMMDD.log`

### Supabase Monitoring

Check prediction tables for fresh data:

- `predictions_ckplus`: Should have today's predictions
- `predictions_notebook`: Should have today's predictions
- Both tables should show all 4 bands (phish, goose, wsp, um)

## ⚙️ Configuration

### Changing Schedule

Edit `.github/workflows/daily-pipeline.yml`:

```yaml
schedule:
  - cron: '0 20 * * *'  # 3 PM ET (20:00 UTC during DST)
```

### Pipeline Parameters

Modify band-specific settings in:

- `src/jambandnerd/predictions/[band]/data_transformer.py`
- `src/jambandnerd/models/ckplus_model.py`
- `src/jambandnerd/models/notebook_model.py`

## 🎯 Success Metrics

### Daily Execution

- **Runtime**: ~20-60 seconds total
- **Success Rate**: Target 99%+ reliability
- **Data Freshness**: Predictions updated daily

### Prediction Quality

- **Coverage**: All active bands generating predictions
- **Consistency**: Stable prediction counts day-over-day
- **Accuracy**: Monitor prediction performance over time

## 📞 Support

### If Something Goes Wrong

1. Check GitHub Actions logs first
2. Verify all secrets are correctly set
3. Test individual components manually
4. Review troubleshooting section above

### Maintenance

- Monitor execution logs weekly
- Update dependencies as needed
- Review prediction accuracy monthly
- Archive old log files periodically

---

## 🎉 You're All Set

Once deployed, your JamBandNerd pipeline will automatically:

- Update WSP data daily at 3 PM ET
- Generate fresh predictions for all bands
- Store results in unified Supabase tables
- Provide comprehensive logging and monitoring

The system is production-ready and designed for reliable, hands-off operation!
