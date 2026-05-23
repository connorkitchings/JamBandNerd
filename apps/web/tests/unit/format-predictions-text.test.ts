import assert from "node:assert/strict";
import test from "node:test";

import { formatTop10Text } from "../../src/lib/format-predictions-text.ts";
import type { PredictionRow } from "../../src/lib/data/index.ts";

function buildRow(songName: string, rank: number): PredictionRow {
  return {
    rank,
    songName,
    lastPlayed: null,
    currentGap: null,
    recentPlays50: null,
    playsPastYear: null,
    avgGap: null,
    recentAvgGap: null,
    gapRatio: null,
    gapZScore: null,
    probability: null,
    tier: "prime",
  };
}

test("formatTop10Text formats full output with venue, location, and top 10 songs", () => {
  const result = formatTop10Text({
    bandName: "Goose",
    dateLabel: "March 27, 2026",
    locationLabel: "New York, NY",
    venueName: "Terminal 5",
    predictions: [
      buildRow("Arrow", 1),
      buildRow("California Magic", 2),
      buildRow("Yeti", 3),
      buildRow("Dripfield", 4),
      buildRow("Empress of Organ", 5),
      buildRow("Hot Tea", 6),
      buildRow("Red Bird", 7),
      buildRow("Spirit of the Dark Horse", 8),
      buildRow("Thatch", 9),
      buildRow("Rockdale", 10),
      buildRow("Slow Stir", 11),
    ],
    shareUrl: "jambandnerd.com/predictions?band=goose",
  });

  assert.ok(result.startsWith("Goose Setlist Predictions\n"));
  assert.ok(result.includes("March 27, 2026"));
  assert.ok(result.includes("Terminal 5 · New York, NY"));
  assert.ok(result.includes("1. Arrow"));
  assert.ok(result.includes("10. Rockdale"));
  assert.ok(!result.includes("11. Slow Stir"), "should not include songs beyond top 10");
  assert.ok(result.endsWith("jambandnerd.com/predictions?band=goose"));
});

test("formatTop10Text handles fewer than 10 predictions gracefully", () => {
  const result = formatTop10Text({
    bandName: "Goose",
    dateLabel: "March 27, 2026",
    locationLabel: "",
    venueName: "",
    predictions: [buildRow("Arrow", 1), buildRow("Yeti", 2)],
    shareUrl: "jambandnerd.com/predictions?band=goose",
  });

  assert.ok(result.includes("1. Arrow"));
  assert.ok(result.includes("2. Yeti"));
  assert.ok(!result.includes("3."));
});

test("formatTop10Text omits sublabel when venue and location are empty", () => {
  const result = formatTop10Text({
    bandName: "Phish",
    dateLabel: "Summer 2026",
    locationLabel: "",
    venueName: "",
    predictions: [buildRow("Tweezer", 1)],
    shareUrl: "jambandnerd.com/predictions?band=phish",
  });

  assert.ok(result.includes("Phish Setlist Predictions"));
  assert.ok(result.includes("Summer 2026"));
  assert.ok(!result.includes(" · "));
});

test("formatTop10Text handles empty predictions array", () => {
  const result = formatTop10Text({
    bandName: "Goose",
    dateLabel: "March 27, 2026",
    locationLabel: "New York, NY",
    venueName: "Terminal 5",
    predictions: [],
    shareUrl: "jambandnerd.com/predictions?band=goose",
  });

  assert.ok(result.includes("Goose Setlist Predictions"));
  assert.ok(result.includes("jambandnerd.com/predictions?band=goose"));
  assert.ok(!result.includes("1."));
});
