import assert from "node:assert/strict";

import test from "node:test";

import { parseSetlistText } from "../../src/lib/admin/setlist-parser.ts";

test("encore maps to set_number 99", () => {
  const rows = parseSetlistText("Encore Porch Song");
  assert.equal(rows.length, 1);
  assert.equal(rows[0].set_number, 99);
  assert.equal(rows[0].song_position, 1);
  assert.equal(rows[0].song_name, "Porch Song");
});

test("positions reset to 1 within each set", () => {
  const rows = parseSetlistText("Set 1 Alpha, Beta\nSet 2 Gamma, Delta");
  assert.deepEqual(
    rows.map((r) => [r.set_number, r.song_position, r.song_name]),
    [
      [1, 1, "Alpha"],
      [1, 2, "Beta"],
      [2, 1, "Gamma"],
      [2, 2, "Delta"],
    ],
  );
});

test("segue splits a chain and flags all but the last", () => {
  const rows = parseSetlistText("Set 1 Alpha > Beta > Gamma, Delta");
  // Alpha, Beta, Gamma are one comma-item chained with >; Delta is separate.
  assert.equal(rows.length, 4);
  assert.deepEqual(
    rows.map((r) => r.is_segue),
    [true, true, false, false],
  );
  assert.equal(rows[2].song_name, "Gamma");
  assert.equal(rows[3].song_name, "Delta");
});

test("comma-titled WSP song stays a single row", () => {
  const rows = parseSetlistText("Set 1 Porch Song, Lawyers, Guns, And Money, Disco");
  assert.equal(rows.length, 3);
  assert.deepEqual(
    rows.map((r) => r.song_name),
    ["Porch Song", "Lawyers, Guns, And Money", "Disco"],
  );
  // Positions must still be sequential after the protected song.
  assert.deepEqual(
    rows.map((r) => r.song_position),
    [1, 2, 3],
  );
});

test("comma-titled song is canonicalized regardless of input case", () => {
  const rows = parseSetlistText("Encore lawyers, guns, and money");
  // Prediction grouping is case-sensitive; the canonical title must be stored
  // so the row matches historical plays of the same song.
  assert.equal(rows.length, 1);
  assert.equal(rows[0].song_name, "Lawyers, Guns, And Money");
});

test("comma song followed by a segue is preserved then split", () => {
  const rows = parseSetlistText(
    "Set 1 Weak Brain, Narrow Mind > Tall Boy",
  );
  assert.equal(rows.length, 2);
  assert.equal(rows[0].song_name, "Weak Brain, Narrow Mind");
  assert.equal(rows[0].is_segue, true);
  assert.equal(rows[1].song_name, "Tall Boy");
  assert.equal(rows[1].is_segue, false);
});

test("curly quotes are normalized to straight apostrophes", () => {
  const rows = parseSetlistText("Set 1 Walkin\u2019 (For Your Love)");
  assert.equal(rows.length, 1);
  assert.equal(rows[0].song_name, "Walkin' (For Your Love)");
});

test("empty or unrecognized input yields no rows", () => {
  assert.deepEqual(parseSetlistText(""), []);
  assert.deepEqual(parseSetlistText("just some text with no set marker"), []);
  assert.deepEqual(parseSetlistText("Set 1\nSet 2"), []);
});
