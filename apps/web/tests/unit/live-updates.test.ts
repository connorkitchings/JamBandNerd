import assert from "node:assert/strict";
import test from "node:test";

import { matchesPredictionUpdateScope } from "../../src/lib/live-updates.ts";

const scope = {
  band: "goose",
  referenceDate: "2026-03-26",
};

test("matchesPredictionUpdateScope accepts canonical payload fields", () => {
  assert.equal(
    matchesPredictionUpdateScope(
      {
        band: "goose",
        reference_date: "2026-03-26",
      },
      scope,
    ),
    true,
  );
});

test("matchesPredictionUpdateScope rejects non-matching updates", () => {
  assert.equal(
    matchesPredictionUpdateScope(
      {
        band: "phish",
        reference_date: "2026-03-26",
      },
      scope,
    ),
    false,
  );
  assert.equal(
    matchesPredictionUpdateScope(
      {
        band: "goose",
        reference_date: "2026-03-27",
      },
      scope,
    ),
    false,
  );
});
