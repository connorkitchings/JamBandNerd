import assert from "node:assert/strict";
import test from "node:test";
import {
  getHostedAuthHeaders,
  normalizeHostedBaseUrl,
  validateHostedAuthResponse,
} from "../smoke/hosted-target.ts";

const preview = "https://jambandnerd-preview.vercel.app";

test("hosted targets normalize to an origin and reject embedded credentials or paths", () => {
  assert.equal(normalizeHostedBaseUrl(), undefined);
  assert.equal(normalizeHostedBaseUrl(`${preview}/`), preview);
  for (const target of [
    `${preview}/predictions`, `${preview}?token=secret`, `${preview}#fragment`,
    "https://user:secret@example.com", "file:///tmp/site", "http://preview.vercel.app",
  ]) {
    assert.throws(() => normalizeHostedBaseUrl(target), /must be an HTTPS/);
  }
});

test("preview bootstrap uses one selected header, never a credential URL", () => {
  assert.deepEqual(getHostedAuthHeaders(preview, "bypass", "oidc"), {
    "x-vercel-protection-bypass": "bypass", "x-vercel-set-bypass-cookie": "true",
  });
  assert.deepEqual(getHostedAuthHeaders(preview, undefined, "oidc"), {
    "x-vercel-trusted-oidc-idp-token": "oidc", "x-vercel-set-bypass-cookie": "true",
  });
  assert.throws(() => getHostedAuthHeaders(preview), /Protected preview smoke requires/);
});

test("preview credentials are withheld from production and lookalike origins", () => {
  for (const target of [undefined, "https://jambandnerd.com", "https://preview.vercel.app.attacker.test"]) {
    assert.equal(getHostedAuthHeaders(target, "bypass", "oidc"), undefined);
  }
});

test("preview bootstrap rejects login redirects and errors without exposing headers", () => {
  validateHostedAuthResponse(preview, 200);
  validateHostedAuthResponse(preview, 307, "/wsp");
  for (const status of [401, 403, 500]) {
    assert.throws(() => validateHostedAuthResponse(preview, status), /authentication failed/);
  }
  assert.throws(() => validateHostedAuthResponse(preview, 302, "https://vercel.com/login"), /outside the configured origin/);
  assert.throws(() => validateHostedAuthResponse(preview, 302, "//attacker.test"), /outside the configured origin/);
});
