import assert from "node:assert/strict";
import test from "node:test";

import {
  buildVenueAnalyticsSnapshot,
  buildVenueKey,
  summarizeVenueOptions,
  type VenueSetlistEntry,
  type VenueShow,
} from "../../src/lib/venue-analytics.ts";

test("buildVenueKey normalizes venue identity into a stable slug", () => {
  const key = buildVenueKey({
    venueName: "Madison Square Garden",
    city: "New York",
    region: "NY",
  });

  assert.equal(key, "madison-square-garden__new-york__ny");
});

test("summarizeVenueOptions sorts by show count and then by recency", () => {
  const shows: VenueShow[] = [
    {
      showId: "1",
      showDate: "2024-01-01",
      venueName: "Red Rocks",
      city: "Morrison",
      region: "CO",
    },
    {
      showId: "2",
      showDate: "2025-01-01",
      venueName: "MSG",
      city: "New York",
      region: "NY",
    },
    {
      showId: "3",
      showDate: "2025-02-01",
      venueName: "Red Rocks",
      city: "Morrison",
      region: "CO",
    },
  ];

  const options = summarizeVenueOptions(shows);

  assert.deepEqual(
    options.map((option) => ({
      label: option.label,
      showCount: option.showCount,
      latestShowDate: option.latestShowDate,
    })),
    [
      {
        label: "Red Rocks • Morrison, CO",
        showCount: 2,
        latestShowDate: "2025-02-01",
      },
      {
        label: "MSG • New York, NY",
        showCount: 1,
        latestShowDate: "2025-01-01",
      },
    ],
  );
});

test("buildVenueAnalyticsSnapshot computes unique songs and average songs per show", () => {
  const shows: VenueShow[] = [
    {
      showId: "show-1",
      showDate: "2024-07-01",
      venueName: "The Fox",
      city: "Atlanta",
      region: "GA",
    },
    {
      showId: "show-2",
      showDate: "2025-07-01",
      venueName: "The Fox",
      city: "Atlanta",
      region: "GA",
    },
  ];
  const setlistEntries: VenueSetlistEntry[] = [
    { showId: "show-1", songName: "Pigeons", setNumber: 1, position: 1 },
    { showId: "show-1", songName: "Fishwater", setNumber: 1, position: 2 },
    { showId: "show-2", songName: "Fishwater", setNumber: 1, position: 1 },
    { showId: "show-2", songName: "Surprise Valley", setNumber: 1, position: 2 },
  ];

  const snapshot = buildVenueAnalyticsSnapshot(shows, setlistEntries);

  assert.equal(snapshot.uniqueSongs, 3);
  assert.equal(snapshot.averageSongsPerShow, 2);
  assert.equal(snapshot.firstShowDate, "2024-07-01");
  assert.equal(snapshot.latestShowDate, "2025-07-01");
});

test("buildVenueAnalyticsSnapshot counts song appearances once per show", () => {
  const shows: VenueShow[] = [
    {
      showId: "show-1",
      showDate: "2024-07-01",
      venueName: "The Fox",
      city: "Atlanta",
      region: "GA",
    },
    {
      showId: "show-2",
      showDate: "2025-07-01",
      venueName: "The Fox",
      city: "Atlanta",
      region: "GA",
    },
  ];
  const setlistEntries: VenueSetlistEntry[] = [
    { showId: "show-1", songName: "Fishwater", setNumber: 1, position: 1 },
    { showId: "show-1", songName: "Fishwater", setNumber: 2, position: 1 },
    { showId: "show-2", songName: "Fishwater", setNumber: 1, position: 1 },
    { showId: "show-2", songName: "Pilgrims", setNumber: 1, position: 2 },
  ];

  const snapshot = buildVenueAnalyticsSnapshot(shows, setlistEntries);

  assert.deepEqual(snapshot.topSongs.slice(0, 2), [
    { songName: "Fishwater", showCount: 2, percentOfShows: 1 },
    { songName: "Pilgrims", showCount: 1, percentOfShows: 0.5 },
  ]);
  assert.deepEqual(
    snapshot.recentShows.map((show) => [show.showDate, show.songCount]),
    [
      ["2025-07-01", 2],
      ["2024-07-01", 2],
    ],
  );
});
