import assert from "node:assert/strict";
import test from "node:test";

import {
  findMissingSetlistShows,
  getDataClock,
  getEasternTodayIso,
  hasDailyIngestionWindowPassed,
  nowFromDataClock,
} from "../../src/lib/show-status.ts";

const INSTANTS = [
  "2026-10-29T03:00:00Z", // evening before in Eastern time
  "2026-10-29T14:00:00Z", // before the 19:15 UTC cutoff
  "2026-10-29T19:14:00Z",
  "2026-10-29T19:15:00Z", // at the cutoff
  "2026-10-29T23:59:00Z",
  "2026-01-15T04:30:00Z", // standard time
];

test("rebuilt clock keeps the Eastern date and the ingestion cutoff state", () => {
  for (const iso of INSTANTS) {
    const real = new Date(iso);
    const rebuilt = nowFromDataClock(getDataClock(real));
    assert.equal(getEasternTodayIso(rebuilt), getEasternTodayIso(real), iso);
    for (const showDate of ["2026-10-28", "2026-10-27", "2026-01-14"]) {
      assert.equal(
        hasDailyIngestionWindowPassed(showDate, rebuilt),
        hasDailyIngestionWindowPassed(showDate, real),
        `${iso} ${showDate}`,
      );
    }
  }
});

test("data clock is serializable and changes only with date or cutoff state", () => {
  const a = getDataClock(new Date("2026-10-29T14:00:00Z"));
  const b = getDataClock(new Date("2026-10-29T15:30:00Z"));
  const c = getDataClock(new Date("2026-10-29T19:15:00Z"));
  assert.deepEqual(a, b);
  assert.notDeepEqual(a, c);
  assert.deepEqual(JSON.parse(JSON.stringify(a)), a);
});

test("missing-setlist detection gives the same answer from a rebuilt clock", () => {
  const showRows = [{ show_id: "1", show_date: "2026-10-28" }];
  const real = new Date("2026-10-29T20:00:00Z");
  const fromReal = findMissingSetlistShows("goose", showRows, [], { now: real });
  const fromClock = findMissingSetlistShows("goose", showRows, [], {
    now: nowFromDataClock(getDataClock(real)),
  });
  assert.deepEqual(fromClock, fromReal);
});
