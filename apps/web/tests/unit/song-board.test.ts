import assert from "node:assert/strict";
import test from "node:test";

import {
  computeTopKHits,
  computeTopKRecall,
  groupPredictionRowsByTier,
  normalizeSongName,
} from "../../src/lib/song-board-core.ts";
import type { PredictionRow } from "../../src/lib/data/index.ts";

function buildRow(songName: string, tier: PredictionRow["tier"], rank: number): PredictionRow {
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
    tier,
  };
}

test("groupPredictionRowsByTier preserves tier order and row order", () => {
  const grouped = groupPredictionRowsByTier([
    buildRow("Song C", "possible", 3),
    buildRow("Song A", "likely", 1),
    buildRow("Song D", "possible", 4),
    buildRow("Song B", "likely", 2),
  ]);

  assert.deepEqual(grouped.likely.map((row) => row.songName), ["Song A", "Song B"]);
  assert.deepEqual(grouped.possible.map((row) => row.songName), ["Song C", "Song D"]);
});

test("normalizeSongName trims and lowercases values for set membership checks", () => {
  assert.equal(normalizeSongName("  Shama Lama Ding Dong "), "shama lama ding dong");
});

test("computeTopKHits counts normalized matches inside the requested window", () => {
  const rows = [
    { songName: "Arcadia" },
    { songName: "  Creatures " },
    { songName: "Hungersite" },
  ];
  const actualSongs = new Set(["creatures", "hungersite"]);

  assert.equal(computeTopKHits(rows, actualSongs, 2), 1);
  assert.equal(computeTopKHits(rows, actualSongs, 3), 2);
});

test("computeTopKRecall returns null for missing actual setlists", () => {
  const rows = [{ songName: "Arcadia" }];

  assert.equal(computeTopKRecall(rows, new Set(), 10), null);
  assert.equal(computeTopKRecall(rows, new Set(["arcadia", "tumble"]), 10), 0.5);
});
