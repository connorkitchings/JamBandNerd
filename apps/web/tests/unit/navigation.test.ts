import assert from "node:assert/strict";
import test from "node:test";

import { buildNavLinks, NAV_ITEMS } from "../../src/lib/navigation.ts";

test("navigation exposes only public single-model routes", () => {
  assert.deepEqual(
    NAV_ITEMS.map((item) => item.label),
    ["Home", "Predictions", "Performance", "Replay"],
  );
  assert.equal(
    NAV_ITEMS.some((item) => /compare/i.test(item.label) || /compare/i.test(item.page)),
    false,
  );
});

test("nav links are built from the current band", () => {
  const links = buildNavLinks("phish", "/phish/predictions");

  assert.deepEqual(
    links.map((link) => link.href),
    ["/phish", "/phish/predictions", "/phish/performance", "/phish/replay"],
  );
});

test("only the link for the current page is active", () => {
  const active = (pathname: string) =>
    buildNavLinks("goose", pathname)
      .filter((link) => link.active)
      .map((link) => link.label);

  assert.deepEqual(active("/goose"), ["Home"]);
  assert.deepEqual(active("/goose/performance"), ["Performance"]);
  assert.deepEqual(active("/goose/replay"), ["Replay"]);
  assert.deepEqual(active("/goose/replay/2026-01-01"), ["Replay"]);
  assert.deepEqual(active("/about"), []);
  assert.deepEqual(active("/phish/predictions"), []);
});
