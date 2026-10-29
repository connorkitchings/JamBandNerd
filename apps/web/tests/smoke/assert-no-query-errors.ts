import { existsSync, readFileSync, rmSync } from "node:fs";

export const SERVER_LOG_PATH = "test-results/server.log";

// Matches the `<label> failed:` line written by failedQuery() in src/lib/data/shows.ts.
const FAILED_QUERY_LINE = /^[\w() ]+ failed:/;
const MAX_REPORTED_LINES = 10;

// Without Supabase env (e.g. CI) no query runs, so this guard is vacuous there.
export default function assertNoQueryErrors() {
  // No log means the server was reused or the run targets a hosted URL: nothing to check.
  if (!existsSync(SERVER_LOG_PATH)) return;

  const lines = readFileSync(SERVER_LOG_PATH, "utf8")
    .split("\n")
    .filter((line) => FAILED_QUERY_LINE.test(line));
  // Remove so a later run that reuses a server cannot read this run's log.
  rmSync(SERVER_LOG_PATH, { force: true });

  if (lines.length === 0) return;
  const shown = lines.slice(0, MAX_REPORTED_LINES).join("\n  ");
  const hidden = lines.length - MAX_REPORTED_LINES;
  const more = hidden > 0 ? `\n  ...and ${hidden} more` : "";
  throw new Error(
    `Server logged ${lines.length} failed data quer${lines.length === 1 ? "y" : "ies"}:\n  ${shown}${more}`,
  );
}
