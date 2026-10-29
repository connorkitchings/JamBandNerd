import assert from "node:assert/strict";
import test from "node:test";

import { getLegacyRedirect } from "../../src/lib/legacy-redirects.ts";

function redirect(pathname: string, query = "") {
  const target = getLegacyRedirect(pathname, new URLSearchParams(query), "goose");
  return target ? `${target.pathname}${target.search}` : null;
}

test("predictions maps to the band predictions page", () => {
  assert.equal(redirect("/predictions", "band=phish"), "/phish/predictions");
});

test("performance carries valid k and metric", () => {
  assert.equal(
    redirect("/performance", "band=wsp&k=25&metric=hits"),
    "/wsp/performance?k=25&metric=hits",
  );
});

test("performance drops invalid k and metric values", () => {
  assert.equal(redirect("/performance", "band=wsp&k=7&metric=bogus"), "/wsp/performance");
});

test("replay maps a valid date into the path", () => {
  assert.equal(redirect("/replay", "band=goose&date=2026-01-01"), "/goose/replay/2026-01-01");
});

test("replay ignores a malformed date", () => {
  assert.equal(redirect("/replay", "band=goose&date=../../x"), "/goose/replay");
});

test("last-show maps to the band replay page", () => {
  assert.equal(redirect("/last-show", "band=billy"), "/billy/replay");
});

test("root with a band maps to the band overview", () => {
  assert.equal(redirect("/", "band=phish"), "/phish");
});

test("root without a band is left to the page", () => {
  assert.equal(redirect("/"), null);
  assert.equal(redirect("/", "teaser=phish"), null);
});

test("a missing band falls back to the default band", () => {
  assert.equal(redirect("/predictions"), "/goose/predictions");
  assert.equal(redirect("/replay", "date=2026-01-01"), "/goose/replay/2026-01-01");
  assert.equal(redirect("/performance", "band="), "/goose/performance");
});

test("band is lowercased", () => {
  assert.equal(redirect("/predictions", "band=Phish"), "/phish/predictions");
});

test("invalid band shapes are not redirected", () => {
  for (const band of ["//evil.com", "../x", "a/b", "goose%2f..", "x y", "-goose", "a".repeat(40)]) {
    assert.equal(redirect("/predictions", `band=${encodeURIComponent(band)}`), null, band);
  }
});

test("other query params are preserved and consumed ones dropped", () => {
  assert.equal(
    redirect("/predictions", "band=phish&utm_source=news&teaser=goose"),
    "/phish/predictions?utm_source=news",
  );
});

test("trailing slashes still match", () => {
  assert.equal(redirect("/predictions/", "band=phish"), "/phish/predictions");
});

test("non-legacy paths are not redirected", () => {
  assert.equal(redirect("/about", "band=phish"), null);
  assert.equal(redirect("/goose/predictions", "band=phish"), null);
  assert.equal(redirect("/api/revalidate"), null);
});
