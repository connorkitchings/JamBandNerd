import assert from "node:assert/strict";
import test from "node:test";

import {
  buildShowDetails,
  isUmDisplayEligibleUpcomingShow,
  selectUmUpcomingShowRow,
} from "../../src/lib/next-show.ts";

test("buildShowDetails maps UM upcoming-show rows into shared show details", () => {
  const details = buildShowDetails({
    starts_at_local: "2026-05-22",
    venue_name: "Pisgah Brewing Company",
    city: "Black Mountain",
    region: "NC",
    country: null,
  });

  assert.deepEqual(details, {
    showDate: "2026-05-22",
    venueName: "Pisgah Brewing Company",
    city: "Black Mountain",
    state: "NC",
    country: null,
    raw: {
      starts_at_local: "2026-05-22",
      venue_name: "Pisgah Brewing Company",
      city: "Black Mountain",
      region: "NC",
      country: null,
    },
  });
});

test("isUmDisplayEligibleUpcomingShow rejects clearly labeled non-UM events", () => {
  assert.equal(
    isUmDisplayEligibleUpcomingShow({
      venue_name: " non-UM | Garcia's Chicago ",
    }),
    false,
  );

  assert.equal(
    isUmDisplayEligibleUpcomingShow({
      venue_name: "Pisgah Brewing Company",
    }),
    true,
  );
});

test("selectUmUpcomingShowRow ignores non-UM events and picks the earliest qualifying date", () => {
  const selected = selectUmUpcomingShowRow([
    {
      starts_at_local: "2026-05-16",
      starts_at: "2026-05-17T00:30:00Z",
      venue_name: "non-UM | Garcia's Chicago",
      city: "Chicago",
      region: "IL",
    },
    {
      starts_at_local: "2026-05-23",
      starts_at: "2026-05-23T23:00:00Z",
      venue_name: "Pisgah Brewing Company",
      city: "Black Mountain",
      region: "NC",
    },
    {
      starts_at_local: "2026-05-22",
      starts_at: "2026-05-22T23:00:00Z",
      venue_name: "Pisgah Brewing Company",
      city: "Black Mountain",
      region: "NC",
    },
  ]);

  assert.equal(selected?.starts_at_local, "2026-05-22");
  assert.equal(selected?.venue_name, "Pisgah Brewing Company");
});

test("selectUmUpcomingShowRow uses starts_at as a tie-breaker for same-day events", () => {
  const selected = selectUmUpcomingShowRow([
    {
      starts_at_local: "2026-06-11",
      starts_at: "2026-06-12T01:00:00Z",
      venue_name: "Late Show",
    },
    {
      starts_at_local: "2026-06-11",
      starts_at: "2026-06-11T23:00:00Z",
      venue_name: "Early Show",
    },
  ]);

  assert.equal(selected?.venue_name, "Early Show");
});

test("selectUmUpcomingShowRow returns null when no eligible UM upcoming rows exist", () => {
  assert.equal(
    selectUmUpcomingShowRow([
      {
        starts_at_local: "2026-05-16",
        venue_name: "non-UM | Garcia's Chicago",
      },
    ]),
    null,
  );
});
