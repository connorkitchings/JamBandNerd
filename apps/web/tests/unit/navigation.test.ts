import assert from "node:assert/strict";
import test from "node:test";

import { DESKTOP_NAV_ITEMS, MOBILE_NAV_ITEMS } from "../../src/lib/navigation.ts";

test("desktop navigation exposes only public single-model routes", () => {
  assert.deepEqual(
    DESKTOP_NAV_ITEMS.map((item) => item.label),
    ["Home", "Predictions", "Performance", "Replay"],
  );
  assert.equal(
    DESKTOP_NAV_ITEMS.some((item) => /compare/i.test(item.label) || item.href === "/compare"),
    false,
  );
});

test("mobile navigation matches desktop navigation ordering", () => {
  assert.deepEqual(
    MOBILE_NAV_ITEMS.map((item) => item.mobileLabel),
    DESKTOP_NAV_ITEMS.map((item) => item.mobileLabel),
  );
  assert.equal(
    MOBILE_NAV_ITEMS.some((item) => /compare/i.test(item.mobileLabel) || item.href === "/compare"),
    false,
  );
});
