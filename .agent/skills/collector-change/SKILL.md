# Collector Change

## When To Use

Use for source adapters, collector fixes, schema normalization, or ingestion reliability work.

## Read Order

1. `.agent/CONTEXT.md`
2. `docs/contributor/developer_guide/architecture.md`
3. `scripts/README.md`
4. Relevant source schema/reference doc under `docs/reference/` or `docs/operations/`
5. Relevant collector module under `src/jambandnerd/data_collection/`

## Rules

- Keep source-specific logic inside the collector path for that band.
- Preserve standardized raw schemas.
- Prefer retries, validation, and normalization over downstream exceptions.

## Expected Validation

- Relevant collector tests
- Targeted collection command for the affected band
- Any freshness or validation script required by the change

## Common Mistakes

- Pushing source-specific cleanup into shared transforms
- Changing raw schema expectations without updating all affected code
- Skipping CI-specific considerations for WSP or remote scraping
