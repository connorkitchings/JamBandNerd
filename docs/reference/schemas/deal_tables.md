# Deal Model Storage Touchpoints

Deal no longer owns dedicated Supabase tables. The active storage contract is:

- canonical prediction rows in `predictions` with `model_slug='deal'`
- derived per-song rows in `prediction_songs`
- scored historical lineage in `historical_prediction_runs`
- per-show evaluation rows in `accuracy_per_show` with `model_version='deal_v2'`

Use the shared schema reference for DDL details:

- [Unified Table Schemas](unified_tables.md)
- [Predictions and Accuracy Schema](../specifications/predictions_schema.md)

Legacy `predictions_deal` and `accuracy_deal` tables remain migration history
only and are removed by the current cleanup sequence.
