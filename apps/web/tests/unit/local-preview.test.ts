import assert from "node:assert/strict";
import test from "node:test";

import {
  getPreviewBands,
  getPreviewLatestPredictions,
  getPreviewReplaySnapshot,
  getPreviewPredictionsForDate,
  shouldUseLocalPreview,
} from "../../src/lib/data/preview.ts";

function restoreEnv(name: string, value: string | undefined) {
  if (typeof value === "string") {
    process.env[name] = value;
  } else {
    delete process.env[name];
  }
}

test("shouldUseLocalPreview defaults to off", () => {
  const originalVercel = process.env.VERCEL;
  const originalPreview = process.env.JAMBNERD_PREVIEW_MODE;

  try {
    delete process.env.VERCEL;
    delete process.env.JAMBNERD_PREVIEW_MODE;
    assert.equal(shouldUseLocalPreview(), false);
  } finally {
    restoreEnv("VERCEL", originalVercel);
    restoreEnv("JAMBNERD_PREVIEW_MODE", originalPreview);
  }
});

test("shouldUseLocalPreview only turns on when explicitly enabled", () => {
  const originalVercel = process.env.VERCEL;
  const originalPreview = process.env.JAMBNERD_PREVIEW_MODE;

  try {
    process.env.VERCEL = "1";
    delete process.env.JAMBNERD_PREVIEW_MODE;
    assert.equal(shouldUseLocalPreview(), false);

    process.env.JAMBNERD_PREVIEW_MODE = "1";
    assert.equal(shouldUseLocalPreview(), true);

    process.env.JAMBNERD_PREVIEW_MODE = "0";
    assert.equal(shouldUseLocalPreview(), false);
  } finally {
    restoreEnv("VERCEL", originalVercel);
    restoreEnv("JAMBNERD_PREVIEW_MODE", originalPreview);
  }
});

test("preview data exposes supported bands and replay snapshots", () => {
  const bands = getPreviewBands();
  assert.equal(bands.length, 4);
  assert.ok(bands.some((band) => band.slug === "goose"));

  const latest = getPreviewLatestPredictions("goose", "deal");
  assert.equal(latest.status, "ready");
  if (latest.status === "ready") {
    assert.equal(latest.snapshot.predictions.length > 0, true);
    assert.equal(latest.snapshot.modelVersion, "deal_preview_v1");
  }

  const replay = getPreviewReplaySnapshot("goose", "2026-04-24");
  assert.equal(replay.status, "ready");
  if (replay.status === "ready") {
    assert.equal(replay.replay.availableShows.length > 0, true);
    assert.equal(replay.replay.selectedDate, "2026-04-24");
  }

  const lastShow = getPreviewPredictionsForDate("goose", "notebook", "2026-04-27");
  assert.equal(lastShow.status, "ready");
});
