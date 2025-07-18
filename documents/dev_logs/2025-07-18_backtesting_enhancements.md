# JamBandNerd Backtesting Enhancement Session - July 18, 2025

## Summary

In this session, we focused on enhancing the historical backtesting framework for JamBandNerd
prediction models. The primary goal was to enable evaluation of both `ckplus` and `notebook`
models with multiple prediction list sizes (25 and 50 songs), ensuring accurate precision, recall,
and F1 metric calculations across multiple bands (Phish, Goose, WSP).

## Key Achievements

1. **Import System Overhaul**:
   - Resolved persistent `ModuleNotFoundError` issues by implementing direct file-based imports
     using `importlib.util` instead of relying on Python's package system
   - Created a self-contained logger implementation in `backtest.py` to eliminate external
     dependencies
   - Added comprehensive path manipulation to resolve module dependencies for both model types

2. **Flexible Data Handling**:
   - Enhanced date column handling to support both `showdate` and `show_date` column names
   - Made the backtest script adaptable to model-specific quirks in function signatures and data columns

3. **Multi-Parameter Testing**:
   - Updated `backtest_all.py` to support testing multiple prediction list sizes (25 and 50) via
     the `--top-n` parameter
   - Implemented parallel execution of backtests for all combinations of bands, models, and top-n
     values

4. **Results**:
   - Successfully executed backtests for all `notebook` models across all bands with both top-25
     and top-50 prediction list sizes
   - Generated evaluation metrics (precision, recall, F1) for notebook models
   - Created CSV output files with detailed per-show metrics

## Current Status

- **Working**: All `notebook` model backtests run successfully with both top-25 and top-50
  prediction list sizes
- **Pending**: `ckplus` model backtests still fail due to import issues that need further investigation
- **Metrics Summary**:
  - Goose/notebook (top-25): Precision: 0.220, Recall: 0.415, F1: 0.286
  - Goose/notebook (top-50): Precision: 0.150, Recall: 0.570, F1: 0.237
  - Phish/notebook (top-25): Precision: 0.260, Recall: 0.356, F1: 0.300
  - Phish/notebook (top-50): Precision: 0.204, Recall: 0.558, F1: 0.299
  - WSP/notebook (top-25): Precision: 0.364, Recall: 0.436, F1: 0.397
  - WSP/notebook (top-50): Precision: 0.250, Recall: 0.600, F1: 0.353

## Next Steps

1. Resolve import issues specific to `ckplus` models:
   - Investigate the `utils.logger` import pattern in ckplus models
   - Create mock modules or implement proper path manipulation for ckplus-specific dependencies

2. Complete full evaluation matrix:
   - Run backtests for all combinations of bands, models, and top-n values
   - Generate comprehensive metrics report for all models

3. Potential improvements:
   - Add unit tests for the backtesting framework
   - Refactor the import system for better maintainability
   - Create visualization tools for comparing model performance

## Technical Notes

- The project structure uses a `src` directory with the `jambandnerd` package
- Direct file imports proved more reliable than package imports in this environment
- Python's `importlib.util` provides a powerful way to load modules directly from file paths
- Parallel execution with `ProcessPoolExecutor` significantly improves efficiency for multiple
  backtests
