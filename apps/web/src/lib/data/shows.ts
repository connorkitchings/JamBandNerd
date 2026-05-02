/**
 * Show-related data fetching — next show, show details, setlist, last show.
 */

import "server-only";

import { cache } from "react";

import type { BandSlug } from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { buildShowDetails, selectUmUpcomingShowRow, type ShowDetails } from "@/lib/next-show";

import { getClientOrState, getBandContext, bandEntryBySlug, getBands } from "./bands";
import {
  getPreviewLastShowSetlist,
  getPreviewNextShowDetails,
  getPreviewSetlistForDate,
  getPreviewShowDetailsByDate,
  shouldUseLocalPreview,
} from "./preview";
import { asRecord, parseNumber, parseStringArray } from "./parsers";
import type { RouteState, SetlistSnapshot, SetlistSong } from "./types";

// ---------------------------------------------------------------------------
// Setlist helpers (used internally and by predictions)
// ---------------------------------------------------------------------------

export async function getSetlistForDate(
  band: BandSlug,
  showDate: string,
): Promise<SetlistSnapshot | null> {
  if (shouldUseLocalPreview()) {
    return getPreviewSetlistForDate(band, showDate);
  }

  const client = getSupabaseServerClient();
  if (!client) {
    return null;
  }

  const bandsState = await getBands();
  if (bandsState.status !== "ready") {
    return null;
  }

  const bandEntry = bandEntryBySlug(bandsState.bands, band);
  if (!bandEntry) {
    return null;
  }

  const { idColumn, showsTable } = bandEntry;
  const positionColumn = band === "phish" ? "position" : "song_position";
  const setlistTable = `${band}_setlists_raw`;

  const { data: showRows, error: showError } = await client
    .from(showsTable)
    .select("*")
    .eq("show_date", showDate)
    .limit(1);

  const showRow = asRecord(showRows?.[0]);
  const showId = showRow?.[idColumn];

  if (showError || !showId) {
    return null;
  }

  const [setlistResponse, detailResponse] = await Promise.all([
    client
      .from(setlistTable)
      .select("*")
      .eq(idColumn, showId)
      .order("set_number", { ascending: true })
      .order(positionColumn, { ascending: true }),
    client.from(showsTable).select("*").eq(idColumn, showId).limit(1),
  ]);

  if (setlistResponse.error || detailResponse.error) {
    return null;
  }

  const seen = new Set<string>();
  const songs: SetlistSong[] =
    setlistResponse.data?.flatMap((item) => {
      const row = asRecord(item);
      if (!row) {
        return [];
      }

      const key = `${row.set_number}-${row[positionColumn]}`;
      if (seen.has(key)) {
        return [];
      }
      seen.add(key);
      return [
        {
          setNumber: parseNumber(row.set_number),
          position: parseNumber(row[positionColumn]),
          songName: String(row.song_name ?? "Unknown Song"),
        },
      ];
    }) ?? [];

  return {
    showDetails: detailResponse.data?.[0] ?? null,
    songs,
  };
}

export function buildFallbackSetlistFromHistoricalRow(
  row: Record<string, unknown> | null,
): SetlistSnapshot | null {
  if (!row) {
    return null;
  }

  const actualSongs = parseStringArray(row.actual_songs);
  if (actualSongs.length === 0) {
    return null;
  }

  return {
    showDetails: null,
    songs: actualSongs.map((songName, index) => ({
      setNumber: null,
      position: index + 1,
      songName,
    })),
  };
}

// ---------------------------------------------------------------------------
// Public cached fetchers
// ---------------------------------------------------------------------------

export const getShowDetailsByDate = cache(
  async (
    bandInput: string | undefined,
    showDate: string | null,
  ): Promise<RouteState<{ band: BandSlug; show: ShowDetails }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; show: ShowDetails }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; show: ShowDetails }>;
    }

    if (shouldUseLocalPreview()) {
      return getPreviewShowDetailsByDate(bandInput, showDate);
    }

    const band = bandState.band;
    if (!showDate) {
      return { status: "empty" };
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { showsTable } = bandState.bandEntry;
      const { data, error } = await client
        .from(showsTable)
        .select("*")
        .eq("show_date", showDate)
        .limit(1);

      if (error) {
        return { status: "error", message: error.message };
      }

      const row = asRecord(data?.[0]);
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band,
        show: buildShowDetails(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getNextShowDetails = cache(
  async (
    bandInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; show: ShowDetails }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; show: ShowDetails }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; show: ShowDetails }>;
    }

    if (shouldUseLocalPreview()) {
      return getPreviewNextShowDetails(bandInput);
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const todayIso = new Date().toISOString().slice(0, 10);
      if (bandState.band === "um") {
        const { data: upcomingData, error: upcomingError } = await client
          .from("um_upcoming_shows")
          .select("*")
          .gte("starts_at_local", todayIso)
          .order("starts_at_local", { ascending: true })
          .order("starts_at", { ascending: true })
          .limit(25);

        if (upcomingError) {
          return { status: "error", message: upcomingError.message };
        }

        const upcomingRows = (upcomingData ?? [])
          .map((item) => asRecord(item))
          .filter((item): item is Record<string, unknown> => item !== null);
        const upcomingRow = selectUmUpcomingShowRow(upcomingRows);

        if (upcomingRow) {
          return {
            status: "ready",
            band: bandState.band,
            show: buildShowDetails(upcomingRow),
          };
        }
      }

      const { data, error } = await client
        .from(bandState.bandEntry.showsTable)
        .select("*")
        .gte("show_date", todayIso)
        .order("show_date", { ascending: true })
        .limit(1);

      if (error) {
        return { status: "error", message: error.message };
      }

      const row = asRecord(data?.[0]);
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band: bandState.band,
        show: buildShowDetails(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getLastShowSetlist = cache(
  async (bandInput: string | undefined): Promise<RouteState<{ band: BandSlug; setlist: SetlistSnapshot }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; setlist: SetlistSnapshot }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; setlist: SetlistSnapshot }>;
    }

    if (shouldUseLocalPreview()) {
      return getPreviewLastShowSetlist(bandInput);
    }

    const band = bandState.band;
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { showsTable } = bandState.bandEntry;
      const todayIso = new Date().toISOString().slice(0, 10);

      const { data: recentShows, error } = await client
        .from(showsTable)
        .select("*")
        .lt("show_date", todayIso)
        .order("show_date", { ascending: false })
        .limit(50);

      if (error) {
        return { status: "error", message: error.message };
      }

      const selectedDate = recentShows?.[0]?.show_date;
      if (typeof selectedDate !== "string") {
        return { status: "empty" };
      }

      const setlist = await getSetlistForDate(band, selectedDate);
      if (!setlist) {
        return { status: "empty" };
      }

      return { status: "ready", band, setlist };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export { getVenueNameFromRow } from "./parsers";
