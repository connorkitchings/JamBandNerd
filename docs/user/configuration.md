# Configuration Guide

This guide covers the main runtime and model configuration surfaces used by the
current JamBandNerd pipeline.

For data architecture and extension rules, use:

- [Pipeline Usage](pipeline_usage.md)
- [Architecture](../contributor/developer_guide/architecture.md)
- [Data Strategy](../reference/specifications/data_strategy.md)

## Environment Configuration

Core pipeline environment variables:

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_pipeline_service_role_key
PHISH_API_KEY=your_phish_net_key
```

Website environment variables live in `apps/web/.env.local`.

## Collector Configuration

Collector defaults live in:

- `src/jambandnerd/data_collection/config.py`
- `src/jambandnerd/data_collection/base.py`

These settings control:

- source base URLs
- request timeouts
- retry behavior
- rate limiting
- cache enablement and cache TTL

Current cache-related environment variables:

- `JAMBN_CACHE_DIR`
- `JAMBN_CACHE_TTL`

## Shared Project Configuration

Shared constants live under `src/jambandnerd/config/`.

Key modules:

- `bands.py`: supported bands, display names, excluded-song config
- `database.py`: prediction and accuracy table names
- `models.py`: model versions, exclusion windows, top-K values, and legacy CK+ thresholds
- `pipeline.py`: common retry/backoff defaults

## Model Configuration

### Notebook

Relevant controls:

- default exclusion window in `src/jambandnerd/config/models.py`
- optional `--exclusion-window` override in prediction and backtest scripts

### Deal

Relevant controls live in:

- model metadata in `src/jambandnerd/models/metadata.py`
- predictor defaults in `src/jambandnerd/models/deal/model.py`
- shared feature generation in `src/jambandnerd/models/deal/features.py`

Deal is the current promoted second model and participates in pipeline,
backfill, per-show accuracy, and website surfaces.

### CK+ (Historical)

Relevant controls in `src/jambandnerd/config/models.py`:

- `RETIREMENT_GAPS`
- `MIN_PLAYS_THRESHOLD_DEFAULT`
- `CKPLUS_ALPHA_DEFAULT`
- `MODEL_VERSIONS`

These values should change only with care, because they affect prediction
behavior and may require a new `model_version`. CK+ is retired and these
settings remain only for historical reference and old stored outputs.

## Adding Bands or Models

User-facing configuration is not the same as platform extension work.

If you are adding a new band or model, use:

- [Extending the Platform](../contributor/developer_guide/extending_the_platform.md)
- [Data Strategy](../reference/specifications/data_strategy.md)
