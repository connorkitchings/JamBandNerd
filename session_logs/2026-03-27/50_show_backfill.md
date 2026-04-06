# Session Log: 2026-03-27

## Summary

Ran 50-show backfills for all three models (Deal, Notebook, CK+) across all 6 bands to compare performance.

## Actions Taken

1. **Ran Deal model backfill** for all bands:
   - goose, eggy, phish, wsp, billy, um

2. **Ran Notebook model backfill** for all bands

3. **Ran CK+ model backfill** for all bands

## Results Summary

### K=10 Hit Rate (avg across bands)
| Model | Avg Hit Rate |
|-------|--------------|
| Notebook | 0.887 |
| CK+ | 0.653 |
| Deal | 0.531 |

### Key Findings
- Notebook significantly outperforms both CK+ and Deal
- Deal (XGBoost) is the worst performer, likely due to uniform probability issue
- CK+ outperforms Deal on most bands

### Band-specific observations
- Billy is the only band where Deal edges out CK+ at K=10 (0.620 vs 0.520)

## Deal Model Issues
The Deal model continues to produce uniform probabilities (~0.9999 for all songs), limiting its ability to differentiate songs. This was identified in previous sessions but not yet resolved.

## Files Modified
- Results saved to database: `accuracy_per_show` table for all band/model combinations
- New model files created: `models/deal/{band}_20260327.json` for each band

## Next Steps
- Investigate and fix the Deal model probability issue
- Consider simplifying the XGBoost approach or using different features
- Run additional backtests with larger show counts to validate findings
