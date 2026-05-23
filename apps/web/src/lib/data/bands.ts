/**
 * Band-related data fetching and selection logic.
 */

import "server-only";

import { cache } from "react";

import { DEFAULT_BAND_SLUG, type BandSlug, normalizeBand } from "@/lib/config";
import { getSupabaseServerClient, hasSupabaseEnv } from "@/lib/supabase/server";

import type { BandEntry, RouteState } from "./types";

// ---------------------------------------------------------------------------
// Supabase env guard (shared by all domain modules)
// ---------------------------------------------------------------------------

export function getClientOrState<T>(): RouteState<T> | null {
  if (!hasSupabaseEnv()) {
    return { status: "missing_env" };
  }

  return null;
}

// ---------------------------------------------------------------------------
// Band fetching
// ---------------------------------------------------------------------------

export const getBands = cache(
  async (): Promise<RouteState<{ bands: BandEntry[] }>> => {
    const missingEnv = getClientOrState<{ bands: BandEntry[] }>();
    if (missingEnv) {
      return missingEnv;
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { data, error } = await client
        .from("bands")
        .select("slug, display_name, shows_table, id_column")
        .eq("is_active", true)
        .order("display_name", { ascending: true });

      if (error) {
        return { status: "error", message: error.message };
      }

      const bands: BandEntry[] =
        data?.map((row) => ({
          slug: String(row.slug),
          displayName: String(row.display_name),
          showsTable: typeof row.shows_table === "string" ? row.shows_table : "",
          idColumn: typeof row.id_column === "string" ? row.id_column : "",
        })) ?? [];

      if (bands.length === 0) {
        return { status: "empty" };
      }

      return { status: "ready", bands };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
);

// ---------------------------------------------------------------------------
// Band selection helpers
// ---------------------------------------------------------------------------

export function bandEntryBySlug(
  bands: BandEntry[],
  slug: string,
): BandEntry | undefined {
  return bands.find((b) => b.slug === slug);
}

export function isValidBandSlug(bands: BandEntry[], slug: string): boolean {
  return bands.some((b) => b.slug === slug);
}

type BandSelection = {
  requestedSlug: string;
  bandEntry: BandEntry | null;
  isInvalid: boolean;
};

export function resolveBandSelection(
  bands: BandEntry[],
  bandInput: string | undefined,
): BandSelection {
  const requestedSlug = normalizeBand(bandInput);
  const matchedBand = bandEntryBySlug(bands, requestedSlug) ?? null;

  if (matchedBand) {
    return {
      requestedSlug,
      bandEntry: matchedBand,
      isInvalid: false,
    };
  }

  if (typeof bandInput === "string" && bandInput.trim().length > 0) {
    return {
      requestedSlug,
      bandEntry: null,
      isInvalid: true,
    };
  }

  return {
    requestedSlug,
    bandEntry: bandEntryBySlug(bands, DEFAULT_BAND_SLUG) ?? bands[0] ?? null,
    isInvalid: false,
  };
}

// ---------------------------------------------------------------------------
// Band context (used by other domain modules)
// ---------------------------------------------------------------------------

export async function getBandContext(
  bandInput: string | undefined,
): Promise<RouteState<{ band: BandSlug; bandEntry: BandEntry }>> {
  const bandsState = await getBands();
  if (bandsState.status !== "ready") {
    return bandsState as RouteState<{ band: BandSlug; bandEntry: BandEntry }>;
  }

  const selection = resolveBandSelection(bandsState.bands, bandInput);
  if (!selection.bandEntry || selection.isInvalid) {
    return { status: "empty" };
  }

  return {
    status: "ready",
    band: selection.bandEntry.slug,
    bandEntry: selection.bandEntry,
  };
}
