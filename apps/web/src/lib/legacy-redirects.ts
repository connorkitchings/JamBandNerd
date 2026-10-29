/**
 * Maps the pre-band-segment URLs (`/predictions?band=goose`, ...) to their
 * `/<band>/...` equivalents. Pure so it can be unit tested; `proxy.ts` applies it.
 */

import { bandPath, isBandSlug, isShowDate, type BandPage } from "./band-routes.ts";
import { DEFAULT_BAND_SLUG } from "./config.ts";

export type LegacyRedirect = { pathname: string; search: string };

/** Query keys consumed by the redirect itself and never forwarded. */
const CONSUMED_KEYS = ["band", "date", "teaser"];

const VALID_K = new Set(["10", "25", "50"]);
const VALID_METRICS = new Set(["coverage", "hits"]);

const PAGE_BY_LEGACY_PATH: Record<string, BandPage> = {
  "/": "overview",
  "/predictions": "predictions",
  "/performance": "performance",
  "/replay": "replay",
  "/last-show": "replay",
};

/**
 * Returns the redirect target for an old-style URL, or `null` when the request
 * is not a legacy URL (or carries an unusable band, which should simply 404).
 *
 * A bare `/` without `?band=` is intentionally not redirected here (see
 * `getRootRedirect`): its target depends on the visitor, so it is never permanent.
 */
export function getLegacyRedirect(
  pathname: string,
  searchParams: URLSearchParams,
  defaultBand: string = DEFAULT_BAND_SLUG,
): LegacyRedirect | null {
  const legacyPath = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const page = PAGE_BY_LEGACY_PATH[legacyPath];
  if (!page) {
    return null;
  }

  const rawBand = searchParams.get("band")?.trim().toLowerCase();
  if (legacyPath === "/" && !rawBand) {
    return null;
  }

  const band = rawBand || defaultBand;
  if (!isBandSlug(band)) {
    return null;
  }

  const rawDate = searchParams.get("date")?.trim();
  const showDate =
    legacyPath === "/replay" && rawDate && isShowDate(rawDate) ? rawDate : null;

  const forwarded = new URLSearchParams();
  for (const [key, value] of searchParams) {
    if (CONSUMED_KEYS.includes(key)) {
      continue;
    }
    if (page === "performance" && key === "k" && !VALID_K.has(value)) {
      continue;
    }
    if (page === "performance" && key === "metric" && !VALID_METRICS.has(value)) {
      continue;
    }
    forwarded.append(key, value);
  }
  const search = forwarded.toString();

  return {
    pathname: bandPath(band, page, showDate),
    search: search ? `?${search}` : "",
  };
}

export type RootRedirect = LegacyRedirect & { permanent: boolean };

/**
 * Decides where a request for exactly `/` goes. An explicit `?band=` is a legacy
 * URL and wins (permanent). Otherwise the visitor's remembered band cookie is used
 * when well-formed, falling back to the default band (temporary, since the answer
 * differs per visitor). A cookie naming a band that no longer exists lands on the
 * band 404 page, which links back to the default band.
 */
export function getRootRedirect(
  searchParams: URLSearchParams,
  cookieBand: string | undefined,
  defaultBand: string = DEFAULT_BAND_SLUG,
): RootRedirect | null {
  if (searchParams.get("band")?.trim()) {
    const legacy = getLegacyRedirect("/", searchParams, defaultBand);
    return legacy && { ...legacy, permanent: true };
  }
  const band = cookieBand && isBandSlug(cookieBand) ? cookieBand : defaultBand;
  return { pathname: bandPath(band), search: "", permanent: false };
}
