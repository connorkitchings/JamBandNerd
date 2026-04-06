import assert from "node:assert/strict";
import test from "node:test";

import { groupPredictionRowsByTier, normalizeSongName } from "../../src/lib/song-board.ts";
import type { PredictionRow } from "../../src/lib/data.ts";

function buildRow(songName: string, tier: PredictionRow["tier"], rank: number): PredictionRow {
  return {
    rank,
    songName,
    lastPlayed: null,
    currentGap: null,
    playsPastYear: null,
    avgGap: null,
    recentAvgGap: null,
    gapRatio: null,
    gapZScore: null,
    ckplusScore: null,
    probability: null,
    tier,
  };
}

test("groupPredictionRowsByTier preserves tier order and row order", () => {
  const grouped = groupPredictionRowsByTier([
    buildRow("Song C", "possible", 3),
    buildRow("Song A", "likely", 1),
    buildRow("Song D", "unlikely", 4),
    buildRow("Song B", "likely", 2),
  ]);

  assert.deepEqual(grouped.likely.map((row) => row.songName), ["Song A", "Song B"]);
  assert.deepEqual(grouped.possible.map((row) => row.songName), ["Song C"]);
  assert.deepEqual(grouped.unlikely.map((row) => row.songName), ["Song D"]);
});

test("normalizeSongName trims and lowercases values for set membership checks", () => {
  assert.equal(normalizeSongName("  Shama Lama Ding Dong "), "shama lama ding dong");
});
