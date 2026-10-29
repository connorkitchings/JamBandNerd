import { notFound } from "next/navigation";

import { pickBandPage, type BandPageContext } from "@/lib/band-page";
import { hasSupabaseEnv } from "@/lib/supabase/server";

import { getBands } from "./bands";

/**
 * Resolves the `[band]` route param for pages and `generateMetadata`; calls
 * `notFound()` for unknown bands. `getBands` is cached, so repeated calls
 * within a request are cheap.
 */
export async function resolveBandPage(slug: string): Promise<BandPageContext> {
  // Without credentials `getBands` would return a deliberately short-lived
  // (request-time) result, which cannot be awaited while prerendering the page
  // shell. Skip it so builds without Supabase env still succeed.
  const bandsState = hasSupabaseEnv()
    ? await getBands()
    : ({ status: "missing_env" } as const);

  return pickBandPage(bandsState, slug, notFound);
}
