/**
 * Pure core of band-page resolution (see `lib/data/resolve-band-page.ts`).
 */

import { isBandSlug } from "./band-routes.ts";
import type { BandSlug } from "./config.ts";
import type { BandEntry, RouteState } from "./data/types.ts";

export type BandPageContext = {
  band: BandSlug;
  bandEntry: BandEntry;
  /** Every active band; empty when the registry could not be loaded. */
  bands: BandEntry[];
};

/**
 * Resolves a URL slug against the band registry. Calls `onUnknown` (which
 * must throw, i.e. Next's `notFound`) for malformed or unregistered slugs.
 *
 * When the registry itself is unavailable (missing env, query error) the slug
 * is trusted so the page can render its own data-state message instead of a 404.
 */
export function pickBandPage(
  bandsState: RouteState<{ bands: BandEntry[] }>,
  slug: string,
  onUnknown: () => never,
): BandPageContext {
  if (!isBandSlug(slug)) {
    return onUnknown();
  }

  const bands = bandsState.status === "ready" ? bandsState.bands : [];
  const bandEntry = bands.find((entry) => entry.slug === slug);
  if (bandEntry) {
    return { band: slug, bandEntry, bands };
  }
  if (bandsState.status === "ready" || bandsState.status === "empty") {
    return onUnknown();
  }

  return {
    band: slug,
    bandEntry: { slug, displayName: slug, showsTable: "", idColumn: "" },
    bands,
  };
}
