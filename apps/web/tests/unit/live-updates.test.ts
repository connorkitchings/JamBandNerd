import assert from "node:assert/strict";
import test from "node:test";

import { matchesPredictionUpdateScope } from "../../src/lib/live-updates.ts";

const scope = {
  band: "goose",
  targetShowKey: "show-1",
  targetShowDate: "2026-03-26",
};

test("matchesPredictionUpdateScope accepts canonical payload fields", () => {
  assert.equal(
    matchesPredictionUpdateScope(
      {
        band: "goose",
        target_show_key: "show-1",
        target_show_date: "2026-03-26",
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
        target_show_key: "show-1",
        target_show_date: "2026-03-26",
      },
      scope,
    ),
    false,
  );
  assert.equal(
    matchesPredictionUpdateScope(
      {
        band: "goose",
        target_show_key: "show-2",
        target_show_date: "2026-03-27",
      },
      scope,
    ),
    false,
  );
});

test("matchesPredictionUpdateScope accepts target show date when key is unavailable", () => {
  assert.equal(
    matchesPredictionUpdateScope(
      {
        band: "goose",
        target_show_date: "2026-03-26",
      },
      { band: "goose", targetShowDate: "2026-03-26" },
    ),
    true,
  );
});
