import assert from "node:assert/strict";
import test from "node:test";

import {
  findMissingSetlistShows,
  hasDailyIngestionWindowPassed,
  shouldShowAfternoonUpdateScheduled,
} from "../../src/lib/show-status.ts";

test("hasDailyIngestionWindowPassed uses 19:15 UTC cutoff on the day after a show (EDT and EST)", () => {
  // Friday Oct 23, 2026 show checked on Saturday Oct 24, 2026
  // Before 19:15 UTC (e.g., 19:14 UTC / 3:14 PM EDT) -> false
  assert.equal(
    hasDailyIngestionWindowPassed(
      "2026-10-23",
      new Date("2026-10-24T19:14:00Z"),
    ),
    false,
  );

  // At 19:15 UTC (3:15 PM EDT) -> true
  assert.equal(
    hasDailyIngestionWindowPassed(
      "2026-10-23",
      new Date("2026-10-24T19:15:00Z"),
    ),
    true,
  );

  // Winter (EST): Nov 13, 2026 show checked on Nov 14, 2026 at 19:15 UTC (2:15 PM EST) -> true
  assert.equal(
    hasDailyIngestionWindowPassed(
      "2026-11-13",
      new Date("2026-11-14T19:15:00Z"),
    ),
    true,
  );

  // Two days after show (morning) -> always true
  assert.equal(
    hasDailyIngestionWindowPassed(
      "2026-10-23",
      new Date("2026-10-25T13:00:00Z"),
    ),
    true,
  );

  // Multi-night hold-off: Sunday Oct 25 before 19:15 UTC, checking Saturday Oct 24
  // when latestPredictionTargetDate is still Friday Oct 23 (< yesterdayIso) -> true
  assert.equal(
    hasDailyIngestionWindowPassed(
      "2026-10-24",
      new Date("2026-10-25T16:00:00Z"),
      "2026-10-23",
    ),
    true,
  );
});

test("shouldShowAfternoonUpdateScheduled only returns true on the morning after a show before 19:15 UTC", () => {
  // Saturday morning before 19:15 UTC for Friday's show -> true
  assert.equal(
    shouldShowAfternoonUpdateScheduled(
      "2026-10-23",
      new Date("2026-10-24T14:00:00Z"),
      false,
    ),
    true,
  );

  // Saturday afternoon after 19:15 UTC -> false
  assert.equal(
    shouldShowAfternoonUpdateScheduled(
      "2026-10-23",
      new Date("2026-10-24T19:20:00Z"),
      false,
    ),
    false,
  );

  // Off-tour / 3 weeks old show -> false
  assert.equal(
    shouldShowAfternoonUpdateScheduled(
      "2026-10-01",
      new Date("2026-10-24T14:00:00Z"),
      false,
    ),
    false,
  );

  // Suppressed when missing setlist notice is active -> false
  assert.equal(
    shouldShowAfternoonUpdateScheduled(
      "2026-10-23",
      new Date("2026-10-24T14:00:00Z"),
      true,
    ),
    false,
  );
});

test("findMissingSetlistShows detects WSP Oct 23 Milwaukee missing setlist after afternoon ingestion", () => {
  const showRows = [
    {
      show_id: "wsp-milwaukee-1",
      show_date: "2026-10-23",
      venue_name: "The Riverside Theater",
      city: "Milwaukee",
      state: "WI",
    },
    {
      show_id: "wsp-milwaukee-2",
      show_date: "2026-10-24",
      venue_name: "The Riverside Theater",
      city: "Milwaukee",
      state: "WI",
    },
  ];

  // Saturday Oct 24 before 19:15 UTC: Oct 23 is not flagged yet
  assert.deepEqual(
    findMissingSetlistShows("wsp", showRows, [], {
      now: new Date("2026-10-24T15:00:00Z"),
    }),
    [],
  );

  // Saturday Oct 24 at 19:20 UTC: Oct 23 is flagged, Oct 24 is tonight so not flagged
  const saturdayAfternoonMissing = findMissingSetlistShows(
    "wsp",
    showRows,
    [],
    {
      now: new Date("2026-10-24T19:20:00Z"),
    },
  );
  assert.equal(saturdayAfternoonMissing.length, 1);
  assert.equal(saturdayAfternoonMissing[0]?.showDate, "2026-10-23");
  assert.equal(saturdayAfternoonMissing[0]?.city, "Milwaukee");
  assert.equal(saturdayAfternoonMissing[0]?.state, "WI");

  // Sunday Oct 25 at 19:30 UTC: both Oct 23 and Oct 24 are flagged if neither has >= 3 songs
  const sundayAfternoonMissing = findMissingSetlistShows("wsp", showRows, [], {
    now: new Date("2026-10-25T19:30:00Z"),
  });
  assert.deepEqual(
    sundayAfternoonMissing.map((s) => s.showDate),
    ["2026-10-23", "2026-10-24"],
  );
});

test("findMissingSetlistShows ignores excluded shows and duplicate show rows when date is covered", () => {
  const phishShows = [
    {
      show_id: "1785867540", // Excluded postponed Huntsville show
      show_date: "2026-10-10",
      venue_name: "Orion Amphitheater",
      city: "Huntsville",
      state: "AL",
    },
  ];
  assert.deepEqual(
    findMissingSetlistShows("phish", phishShows, [], {
      now: new Date("2026-10-12T20:00:00Z"),
    }),
    [],
  );

  // Duplicate raw show rows on the same date where one show_id has >= 3 unique songs
  const duplicateWspShows = [
    {
      show_id: "wsp-dup-empty",
      show_date: "2026-10-23",
      venue_name: "The Riverside Theater",
      city: "Milwaukee",
      state: "WI",
    },
    {
      show_id: "wsp-dup-populated",
      show_date: "2026-10-23",
      venue_name: "The Riverside Theater",
      city: "Milwaukee",
      state: "WI",
    },
  ];
  const setlists = [
    { show_id: "wsp-dup-populated", song_name: "Porch Song" },
    { show_id: "wsp-dup-populated", song_name: "Chilly Water" },
    { show_id: "wsp-dup-populated", song_name: "Tall Boy" },
  ];
  assert.deepEqual(
    findMissingSetlistShows("wsp", duplicateWspShows, setlists, {
      now: new Date("2026-10-24T20:00:00Z"),
    }),
    [],
  );
});
