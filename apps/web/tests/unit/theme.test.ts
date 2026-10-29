import assert from "node:assert/strict";
import test from "node:test";

import { THEME_INIT_SCRIPT, THEME_STORAGE_KEY } from "../../src/lib/theme.ts";

function runScript(stored: string | null, throws = false) {
  const attrs: Record<string, string> = {};
  const sandbox = {
    localStorage: {
      getItem(key: string) {
        if (throws) throw new Error("blocked");
        return key === THEME_STORAGE_KEY ? stored : null;
      },
    },
    document: { documentElement: { setAttribute: (k: string, v: string) => (attrs[k] = v) } },
  };
  new Function("localStorage", "document", THEME_INIT_SCRIPT)(sandbox.localStorage, sandbox.document);
  return attrs;
}

test("theme init script applies a stored dark or light choice", () => {
  assert.deepEqual(runScript("dark"), { "data-theme": "dark" });
  assert.deepEqual(runScript("light"), { "data-theme": "light" });
});

test("theme init script ignores unknown values and unavailable storage", () => {
  assert.deepEqual(runScript("purple"), {});
  assert.deepEqual(runScript(null), {});
  assert.deepEqual(runScript(null, true), {});
});
