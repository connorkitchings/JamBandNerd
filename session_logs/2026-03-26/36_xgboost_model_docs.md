# Deal Model Documentation

## Goal

Build out documentation for a new Deal prediction model that will coexist with existing Notebook and CK+ models.

## Constraints

- Model must remain hidden from public website until explicit user approval
- Backend must be fully wired and generating predictions for review
- Use methodology from twinfield10/Widespread-Panic-Setlists as inspiration but not exact copy

## Commands Run

```bash
# No commands - documentation only
```

## Files Created

- `docs/reference/models/xgboost.md` - Full model documentation including:
  - Overview and design principles
  - How it runs (pipeline integration)
  - Feature engineering (temporal windows, frequency, LTP features)
  - Training data generation
  - Model configuration
  - Ranking and output format
  - Historical accuracy measurement
  - Storage schema
  - Website visibility control
  - Next steps

## Files Modified

- `docs/reference/models/index.md` - Added XGBoost to model list
- `docs/index.md` - Added XGBoost to models reference in nav

## Validation

- Documentation follows same structure as existing model docs (notebook.md, ckplus.md)
- All pipeline usage examples mirror existing patterns
- Website visibility control documented with code example

## Next Step

When approved for implementation:
1. Add `xgboost>=2.0.0` to `pyproject.toml`
2. Create `src/jambandnerd/models/xgboost/` module
3. Implement feature engineering
4. Wire into prediction pipeline
5. Enable website visibility upon approval
