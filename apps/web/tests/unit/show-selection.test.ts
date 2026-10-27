import assert from "node:assert/strict";
import test from "node:test";

import type { ShowDetails } from "../../src/lib/next-show.ts";
import {
  countRowsByShowId,
  filterExcludedShows,
  pickShowWithMostSongs,
  selectTeaserShow,
} from "../../src/lib/show-selection.ts";

// 1755099318 is a Goose show id in EXCLUDED_PREDICTION_SHOW_IDS (TV appearance).
const EXCLUDED_GOOSE_ID = "1755099318";

function show(showDate: string, venueName: string): ShowDetails {
  return { showDate, venueName, city: null, state: null, country: null, raw: {} };
}

test("filterExcludedShows drops excluded ids for the band only", () => {
  const rows = [{ show_id: EXCLUDED_GOOSE_ID }, { show_id: "keep" }];

  assert.deepEqual(filterExcludedShows("goose", rows, "show_id"), [{ show_id: "keep" }]);
  assert.equal(filterExcludedShows("wsp", rows, "show_id").length, 2);
});

test("filterExcludedShows matches numeric ids against string config", () => {
  const rows = [{ show_id: Number(EXCLUDED_GOOSE_ID) }, { show_id: 1 }];

  assert.deepEqual(filterExcludedShows("goose", rows, "show_id"), [{ show_id: 1 }]);
});

test("pickShowWithMostSongs prefers the full show over a short set on the same date", () => {
  const rows = [{ show_id: "promo" }, { show_id: "full" }];
  const counts = countRowsByShowId(
    [
      { show_id: "promo" },
      { show_id: "full" },
      { show_id: "full" },
      { show_id: "full" },
    ],
    "show_id",
  );

  assert.deepEqual(pickShowWithMostSongs(rows, "show_id", counts), { show_id: "full" });
});

test("pickShowWithMostSongs keeps the first row when no show has songs", () => {
  const rows = [{ show_id: "a" }, { show_id: "b" }];

  assert.deepEqual(pickShowWithMostSongs(rows, "show_id", new Map()), { show_id: "a" });
  assert.equal(pickShowWithMostSongs([], "show_id", new Map()), null);
});

test("selectTeaserShow uses the next show only when it matches the snapshot date", () => {
  const next = show("2026-11-01", "Next Venue");
  const snapshotShow = show("2026-10-30", "Snapshot Venue");

  assert.equal(selectTeaserShow("2026-11-01", next, snapshotShow), next);
  assert.equal(selectTeaserShow("2026-10-30", next, snapshotShow), snapshotShow);
  assert.equal(selectTeaserShow("2026-10-30", next, null), null);
  assert.equal(selectTeaserShow("2026-10-30", null, snapshotShow), snapshotShow);
});
