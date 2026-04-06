import assert from "node:assert/strict";
import test from "node:test";

import { selectLivePredictionSeedRow } from "../../src/lib/prediction-selection.ts";

test("selectLivePredictionSeedRow prefers the nearest future reference date over a newer historical write", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-03-28",
        predicted_at: "2026-03-30T14:12:05.742793+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2026-04-10",
        predicted_at: "2026-03-30T14:11:58.955599+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-03-30" },
  );

  assert.equal(selected?.reference_date, "2026-04-10");
});

test("selectLivePredictionSeedRow picks the earliest future reference date when multiple future rows exist", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-04-12",
        predicted_at: "2026-03-30T15:00:00+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2026-04-10",
        predicted_at: "2026-03-30T14:00:00+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-03-30" },
  );

  assert.equal(selected?.reference_date, "2026-04-10");
});

test("selectLivePredictionSeedRow falls back to the newest historical row when no future rows exist", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-03-28",
        predicted_at: "2026-03-30T14:12:05.742793+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2025-12-13",
        predicted_at: "2026-03-28T19:11:41.427945+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-04-20" },
  );

  assert.equal(selected?.reference_date, "2026-03-28");
});
