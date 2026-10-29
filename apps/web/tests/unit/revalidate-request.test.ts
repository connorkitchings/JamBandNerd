import assert from "node:assert/strict";
import test from "node:test";

import {
  handleRevalidateRequest,
  type RevalidateDeps,
} from "../../src/lib/revalidate-request.ts";

const SECRET = "s3cret-token";

function setup(overrides: Partial<RevalidateDeps> = {}) {
  const revalidated: string[] = [];
  const deps: RevalidateDeps = {
    secret: SECRET,
    getBandSlugs: async () => ["goose", "phish"],
    revalidate: (tag) => revalidated.push(tag),
    ...overrides,
  };
  return { deps, revalidated };
}

function post(body: unknown, token: string | null = SECRET) {
  return new Request("https://example.test/api/revalidate", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...(token === null ? {} : { authorization: `Bearer ${token}` }),
    },
    body: typeof body === "string" ? body : JSON.stringify(body),
  });
}

test("missing token is rejected with 401 and revalidates nothing", async () => {
  const { deps, revalidated } = setup();
  const response = await handleRevalidateRequest(post({ band: "goose" }, null), deps);
  assert.equal(response.status, 401);
  assert.deepEqual(revalidated, []);
});

test("wrong token (same and different length) is rejected with 401", async () => {
  for (const token of ["s3cret-tokeX", "short"]) {
    const { deps, revalidated } = setup();
    const response = await handleRevalidateRequest(post({ band: "goose" }, token), deps);
    assert.equal(response.status, 401);
    assert.deepEqual(revalidated, []);
  }
});

test("unset secret fails closed even for an empty or matching-looking token", async () => {
  for (const secret of [undefined, ""]) {
    const { deps, revalidated } = setup({ secret });
    const response = await handleRevalidateRequest(post({ band: "goose" }, ""), deps);
    assert.equal(response.status, 401);
    assert.deepEqual(revalidated, []);
  }
});

test("non-POST request gets 405 with an Allow header", async () => {
  const { deps, revalidated } = setup();
  const request = new Request("https://example.test/api/revalidate", {
    method: "GET",
    headers: { authorization: `Bearer ${SECRET}` },
  });
  const response = await handleRevalidateRequest(request, deps);
  assert.equal(response.status, 405);
  assert.equal(response.headers.get("allow"), "POST");
  assert.deepEqual(revalidated, []);
});

test("correct token and known band revalidates that band's tag", async () => {
  const { deps, revalidated } = setup();
  const response = await handleRevalidateRequest(post({ band: "goose" }), deps);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), { revalidated: true, band: "goose" });
  assert.deepEqual(revalidated, ["band:goose"]);
});

test("unknown, missing, or malformed band is rejected with 400", async () => {
  for (const body of [{ band: "nope" }, {}, { band: 5 }, { band: "" }, "not json", "null"]) {
    const { deps, revalidated } = setup();
    const response = await handleRevalidateRequest(post(body), deps);
    assert.equal(response.status, 400, JSON.stringify(body));
    assert.deepEqual(revalidated, []);
  }
});

test("unavailable band list returns 503 without revalidating", async () => {
  const { deps, revalidated } = setup({ getBandSlugs: async () => null });
  const response = await handleRevalidateRequest(post({ band: "goose" }), deps);
  assert.equal(response.status, 503);
  assert.deepEqual(revalidated, []);
});

test("error bodies do not echo the secret or the submitted band", async () => {
  const { deps } = setup();
  const response = await handleRevalidateRequest(post({ band: "<script>x</script>" }), deps);
  const text = await response.text();
  assert.equal(text.includes("script"), false);
  assert.equal(text.includes(SECRET), false);
});
