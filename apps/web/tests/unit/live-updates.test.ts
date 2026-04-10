import assert from "node:assert/strict";
import test from "node:test";

import { matchesPredictionUpdateScope } from "../../src/lib/live-updates.ts";

const scope = {
  band: "goose",
  model: "notebook",
  referenceDate: "2026-03-26",
};

test("matchesPredictionUpdateScope accepts canonical prediction_songs payload fields", () => {
  assert.equal(
    matchesPredictionUpdateScope(
      {
        band: "goose",
        model_slug: "notebook",
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
        model_slug: "notebook",
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
        model_slug: "deal",
        reference_date: "2026-03-26",
      },
      scope,
    ),
    false,
  );
});
