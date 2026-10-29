import "server-only";

import { cacheLife } from "next/cache";

import type { RouteState } from "./types";

/**
 * Cache lifetime for a band's data, called from inside a `"use cache"` scope.
 *
 * - Successful reads live for days; the daily pipeline calls the revalidate
 *   route to expire them as soon as new data lands.
 * - Failed reads (`error`, `missing_env`) must not stick, so they expire in
 *   seconds and are retried on the next request.
 * - `live` marks data a realtime subscriber refreshes mid-show. A zero
 *   `revalidate` makes the entry dynamic, so `router.refresh()` always reads
 *   fresh rows.
 */
export function applyBandCacheLife(
  status: RouteState<unknown>["status"],
  options: { live?: boolean } = {},
) {
  if (options.live) {
    cacheLife({ stale: 0, revalidate: 0, expire: 60 });
    return;
  }
  if (status === "ready") {
    cacheLife("days");
  } else if (status === "empty") {
    cacheLife("hours");
  } else {
    cacheLife("seconds");
  }
}
