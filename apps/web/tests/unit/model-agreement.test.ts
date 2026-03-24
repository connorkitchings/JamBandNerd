import assert from "node:assert/strict";
import test from "node:test";

import { calculateModelAgreement } from "../../src/lib/model-agreement.ts";
import type { PredictionRow } from "../../src/lib/data.ts";

function buildRows(songNames: string[]): PredictionRow[] {
  return songNames.map((songName, index) => ({
    rank: index + 1,
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
    tier: "possible",
  }));
}

test("calculateModelAgreement only counts overlap within each model's top-k slice", () => {
  const primaryRows = buildRows([
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
  ]);
  const secondaryRows = buildRows([
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "A",
    "B",
  ]);

  const agreement = calculateModelAgreement(primaryRows, secondaryRows);

  assert.ok(agreement);
  assert.equal(agreement.top10.matchCount, 0);
  assert.equal(agreement.top10.total, 10);
  assert.equal(agreement.top25.matchCount, 4);
  assert.equal(agreement.top25.total, 12);
});

test("calculateModelAgreement uses actual available list sizes for composite weighting", () => {
  const primaryRows = buildRows(["A", "B", "C"]);
  const secondaryRows = buildRows(["A", "X", "Y"]);

  const agreement = calculateModelAgreement(primaryRows, secondaryRows);

  assert.ok(agreement);
  assert.equal(agreement.top10.matchCount, 1);
  assert.equal(agreement.top10.total, 3);
  assert.equal(agreement.top25.total, 3);
  assert.equal(agreement.top50.total, 3);
  assert.equal(agreement.composite, 1 / 3);
});
