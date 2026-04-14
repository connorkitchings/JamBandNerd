-- Drop legacy per-model prediction tables now that all data lives in the
-- unified `predictions` table (created in 20260413_consoldiate_predictions_table.sql).

DROP TABLE IF EXISTS public.predictions_notebook;
DROP TABLE IF EXISTS public.predictions_deal;
DROP TABLE IF EXISTS public.predictions_ckplus;

-- Drop legacy aggregate accuracy tables. All metrics are derivable from
-- `accuracy_per_show` and `historical_prediction_runs`.

DROP TABLE IF EXISTS public.notebook_accuracy;
DROP TABLE IF EXISTS public.accuracy_ckplus;
DROP TABLE IF EXISTS public.accuracy_deal;
