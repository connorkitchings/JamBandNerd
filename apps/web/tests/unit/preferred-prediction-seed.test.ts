import assert from "node:assert/strict";
import test from "node:test";

import { selectPreferredPredictionSeed } from "../../src/lib/preferred-prediction-seed.ts";

test("selectPreferredPredictionSeed prefers future shows over stale historical predictions", () => {
  const rows = [
    {
      target_show_date: "2026-05-08",
      reference_date: "2026-05-08",
      generated_at: "2026-05-08T19:35:00Z",
      model_version: "notebook_v1",
    },
    {
      target_show_date: "2026-05-10",
      reference_date: "2026-05-10",
      generated_at: "2026-05-09T19:30:00Z",
      model_version: "notebook_v1",
    },
  ];

  const selected = selectPreferredPredictionSeed(rows, {
    todayIso: "2026-05-09",
  });

  assert.equal(selected?.target_show_date, "2026-05-10");
  assert.equal(selected?.reference_date, "2026-05-10");
});

test("selectPreferredPredictionSeed picks the earliest future show when multiple exist", () => {
  const rows = [
    {
      target_show_date: "2026-05-12",
      reference_date: "2026-05-12",
      generated_at: "2026-05-09T20:00:00Z",
      model_version: "notebook_v1",
    },
    {
      target_show_date: "2026-05-10",
      reference_date: "2026-05-10",
      generated_at: "2026-05-09T19:30:00Z",
      model_version: "notebook_v1",
    },
    {
      target_show_date: "2026-05-11",
      reference_date: "2026-05-11",
      generated_at: "2026-05-09T19:45:00Z",
      model_version: "notebook_v1",
    },
  ];

  const selected = selectPreferredPredictionSeed(rows, {
    todayIso: "2026-05-09",
  });

  assert.equal(selected?.target_show_date, "2026-05-10");
});

test("selectPreferredPredictionSeed falls back to most recent historical when no future shows exist", () => {
  const rows = [
    {
      target_show_date: "2026-05-07",
      reference_date: "2026-05-07",
      generated_at: "2026-05-07T19:30:00Z",
      model_version: "notebook_v1",
    },
    {
      target_show_date: "2026-05-08",
      reference_date: "2026-05-08",
      generated_at: "2026-05-08T19:35:00Z",
      model_version: "notebook_v1",
    },
  ];

  const selected = selectPreferredPredictionSeed(rows, {
    todayIso: "2026-05-09",
  });

  assert.equal(selected?.target_show_date, "2026-05-08");
});

test("selectPreferredPredictionSeed handles the exact bug scenario: stale May 8 prediction on May 9", () => {
  const rows = [
    {
      target_show_date: "2026-05-08",
      reference_date: "2026-05-08",
      generated_at: "2026-05-08T19:35:00Z",
      model_version: "notebook_v1",
    },
  ];

  const selected = selectPreferredPredictionSeed(rows, {
    todayIso: "2026-05-09",
  });

  assert.equal(selected?.target_show_date, "2026-05-08");
  assert.equal(selected?.reference_date, "2026-05-08");
});

test("selectPreferredPredictionSeed returns null for empty input", () => {
  const selected = selectPreferredPredictionSeed([], {
    todayIso: "2026-05-09",
  });

  assert.equal(selected, null);
});

test("selectPreferredPredictionSeed prefers today's show over yesterday's", () => {
  const rows = [
    {
      target_show_date: "2026-05-08",
      reference_date: "2026-05-08",
      generated_at: "2026-05-08T19:35:00Z",
      model_version: "notebook_v1",
    },
    {
      target_show_date: "2026-05-09",
      reference_date: "2026-05-09",
      generated_at: "2026-05-09T15:00:00Z",
      model_version: "notebook_v1",
    },
  ];

  const selected = selectPreferredPredictionSeed(rows, {
    todayIso: "2026-05-09",
  });

  assert.equal(selected?.target_show_date, "2026-05-09");
});

test("selectPreferredPredictionSeed uses generated_at as tie-breaker for same target date", () => {
  const rows = [
    {
      target_show_date: "2026-05-10",
      reference_date: "2026-05-10",
      generated_at: "2026-05-09T18:00:00Z",
      model_version: "notebook_v1",
    },
    {
      target_show_date: "2026-05-10",
      reference_date: "2026-05-10",
      generated_at: "2026-05-09T20:00:00Z",
      model_version: "notebook_v1",
    },
  ];

  const selected = selectPreferredPredictionSeed(rows, {
    todayIso: "2026-05-09",
  });

  assert.equal(selected?.generated_at, "2026-05-09T20:00:00Z");
});
