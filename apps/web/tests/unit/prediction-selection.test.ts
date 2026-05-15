import assert from "node:assert/strict";
import test from "node:test";

import { selectLivePredictionSeedRow } from "../../src/lib/prediction-selection.ts";

test("selectLivePredictionSeedRow prefers the nearest future target date over a newer stale write", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-03-28",
        target_show_date: "2026-03-28",
        target_show_key: "show-previous",
        predicted_at: "2026-03-30T14:12:05.742793+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2026-04-09",
        target_show_date: "2026-04-10",
        target_show_key: "show-next",
        predicted_at: "2026-03-30T14:11:58.955599+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-03-30" },
  );

  assert.equal(selected?.target_show_key, "show-next");
});

test("selectLivePredictionSeedRow picks the earliest future target date when multiple future rows exist", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-04-11",
        target_show_date: "2026-04-12",
        target_show_key: "show-2",
        predicted_at: "2026-03-30T15:00:00+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2026-04-09",
        target_show_date: "2026-04-10",
        target_show_key: "show-1",
        predicted_at: "2026-03-30T14:00:00+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-03-30" },
  );

  assert.equal(selected?.target_show_date, "2026-04-10");
});

test("selectLivePredictionSeedRow treats today as the active live-show target", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-04-09",
        target_show_date: "2026-04-10",
        target_show_key: "show-tonight",
        predicted_at: "2026-03-30T14:12:05.742793+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2026-04-11",
        target_show_date: "2026-04-12",
        target_show_key: "show-future",
        predicted_at: "2026-03-30T14:12:05.742793+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-04-10" },
  );

  assert.equal(selected?.target_show_key, "show-tonight");
});

test("selectLivePredictionSeedRow falls back to the newest stale row when no future rows exist", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-03-27",
        target_show_date: "2026-03-28",
        target_show_key: "show-newer",
        predicted_at: "2026-03-30T14:12:05.742793+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2025-12-12",
        target_show_date: "2025-12-13",
        target_show_key: "show-older",
        predicted_at: "2026-03-28T19:11:41.427945+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-04-20" },
  );

  assert.equal(selected?.target_show_key, "show-newer");
});

test("selectLivePredictionSeedRow uses newest generated timestamp for target-date ties", () => {
  const selected = selectLivePredictionSeedRow(
    [
      {
        reference_date: "2026-04-09",
        target_show_date: "2026-04-10",
        target_show_key: "show-old-write",
        predicted_at: "2026-03-30T14:00:00+00:00",
        model_version: "notebook_v1",
      },
      {
        reference_date: "2026-04-09",
        target_show_date: "2026-04-10",
        target_show_key: "show-new-write",
        predicted_at: "2026-03-30T15:00:00+00:00",
        model_version: "notebook_v1",
      },
    ],
    { todayIso: "2026-04-01" },
  );

  assert.equal(selected?.target_show_key, "show-new-write");
});
