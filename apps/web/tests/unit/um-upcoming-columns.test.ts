import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import test from "node:test";

import { UM_UPCOMING_SHOW_COLUMNS } from "../../src/lib/data/um-upcoming-columns.ts";

const MIGRATIONS_DIR = new URL("../../../../supabase/migrations/", import.meta.url);
const TABLE = "um_upcoming_shows";
const CONSTRAINT_KEYWORDS = new Set([
  "primary",
  "unique",
  "constraint",
  "foreign",
  "check",
  "like",
]);

function readMigrations() {
  return readdirSync(MIGRATIONS_DIR)
    .filter((name) => name.endsWith(".sql"))
    .sort()
    .map((name) => readFileSync(new URL(name, MIGRATIONS_DIR), "utf8"));
}

function tableColumnsFromMigrations() {
  const columns = new Set<string>();
  const createRe = new RegExp(
    `create\\s+table\\s+(?:if\\s+not\\s+exists\\s+)?(?:public\\.)?${TABLE}\\s*\\(([\\s\\S]*?)\\n\\s*\\)\\s*;`,
    "gi",
  );
  const addRe = new RegExp(
    `alter\\s+table\\s+(?:if\\s+exists\\s+)?(?:only\\s+)?(?:public\\.)?${TABLE}\\b([^;]*);`,
    "gi",
  );

  for (const sql of readMigrations()) {
    for (const [, body] of sql.matchAll(createRe)) {
      for (const line of body.split("\n")) {
        const name = line.trim().split(/\s+/)[0]?.replace(/"/g, "").toLowerCase();
        if (name && !CONSTRAINT_KEYWORDS.has(name)) columns.add(name);
      }
    }
    for (const [, clauses] of sql.matchAll(addRe)) {
      for (const [, name] of clauses.matchAll(
        /add\s+column\s+(?:if\s+not\s+exists\s+)?"?(\w+)"?/gi,
      )) {
        columns.add(name.toLowerCase());
      }
    }
  }
  return columns;
}

test("test_migration_parser_finds_create_table_columns", () => {
  const columns = tableColumnsFromMigrations();

  assert.ok(columns.has("source_uuid"));
  assert.ok(columns.has("starts_at_local"));
});

test("test_um_upcoming_select_columns_all_exist_in_migrations", () => {
  const known = tableColumnsFromMigrations();
  const selected = UM_UPCOMING_SHOW_COLUMNS.split(",").map((c) => c.trim());

  const missing = selected.filter((column) => !known.has(column));

  assert.deepEqual(missing, [], `columns not in ${TABLE}: ${missing.join(", ")}`);
});
