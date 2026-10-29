import assert from "node:assert/strict";
import test from "node:test";

import { pickBandPage } from "../../src/lib/band-page.ts";

const goose = { slug: "goose", displayName: "Goose", showsTable: "goose_shows", idColumn: "id" };
const phish = { slug: "phish", displayName: "Phish", showsTable: "phish_shows", idColumn: "id" };

class NotFoundSignal extends Error {}
function notFound(): never {
  throw new NotFoundSignal();
}

const ready = { status: "ready" as const, bands: [goose, phish] };

test("known band returns its context", () => {
  const context = pickBandPage(ready, "phish", notFound);

  assert.equal(context.band, "phish");
  assert.equal(context.bandEntry, phish);
  assert.deepEqual(context.bands, [goose, phish]);
});

test("unknown band calls notFound", () => {
  assert.throws(() => pickBandPage(ready, "nobody", notFound), NotFoundSignal);
});

test("malformed slug calls notFound without consulting the registry", () => {
  assert.throws(() => pickBandPage(ready, "../etc", notFound), NotFoundSignal);
  assert.throws(() => pickBandPage(ready, "Goose", notFound), NotFoundSignal);
});

test("empty registry calls notFound", () => {
  assert.throws(() => pickBandPage({ status: "empty" }, "goose", notFound), NotFoundSignal);
});

test("unavailable registry trusts the slug so the page can show its data state", () => {
  for (const state of [
    { status: "missing_env" as const },
    { status: "error" as const, message: "boom" },
  ]) {
    const context = pickBandPage(state, "goose", notFound);

    assert.equal(context.band, "goose");
    assert.deepEqual(context.bands, []);
  }
});
