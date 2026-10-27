/**
 * Show-related data fetching — next show, show details, setlist, last show.
 */

import "server-only";

import { cache } from "react";

import type { BandSlug } from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { buildShowDetails, selectUmUpcomingShowRow, type ShowDetails } from "@/lib/next-show";
import {
  findMissingSetlistShows,
  getEasternDateOffsetIso,
  getEasternTodayIso,
  type MissingSetlistShow,
} from "@/lib/show-status";

import {
  countRowsByShowId,
  filterExcludedShows,
  pickShowWithMostSongs,
} from "@/lib/show-selection";

import { getClientOrState, getBandContext, bandEntryBySlug, getBands } from "./bands";
import {
  asRecord,
  buildSetlistSelectColumns,
  parseNumber,
  parseSetNumber,
} from "./parsers";
import type { RouteState, SetlistSnapshot, SetlistSong } from "./types";

const DEFAULT_SHOW_DETAILS_COLUMNS =
  "show_date, venue_name, venue_city, venue_state, venue_country";
const WSP_SHOW_DETAILS_COLUMNS = "show_date, venue_name, city, state";
const UM_UPCOMING_SHOW_COLUMNS =
  "starts_at_local, starts_at, show_date, venue_name, venue, venue_city, city, region, venue_state, state, venue_country, country";

function showDetailsColumns(band: BandSlug, idColumn?: string) {
  const columns =
    band === "wsp" ? WSP_SHOW_DETAILS_COLUMNS : DEFAULT_SHOW_DETAILS_COLUMNS;
  return idColumn ? `${idColumn}, ${columns}` : columns;
}

// Raw error text stays in server logs; callers render a generic message.
function failedQuery(
  label: string,
  error: unknown,
): { status: "error"; message: string } {
  console.error(`${label} failed:`, error);
  return { status: "error", message: "Data query failed" };
}

// ---------------------------------------------------------------------------
// Setlist helpers (used internally and by predictions)
// ---------------------------------------------------------------------------

type SetlistLookup =
  | { status: "ready"; setlist: SetlistSnapshot }
  | { status: "empty" }
  | { status: "error" };

export async function getSetlistForDate(
  band: BandSlug,
  showDate: string,
): Promise<SetlistSnapshot | null> {
  const lookup = await lookupSetlistForDate(band, showDate);
  return lookup.status === "ready" ? lookup.setlist : null;
}

async function lookupSetlistForDate(
  band: BandSlug,
  showDate: string,
): Promise<SetlistLookup> {
  const client = getSupabaseServerClient();
  if (!client) {
    return { status: "empty" };
  }

  const bandsState = await getBands();
  if (bandsState.status !== "ready") {
    return { status: "error" };
  }

  const bandEntry = bandEntryBySlug(bandsState.bands, band);
  if (!bandEntry) {
    return { status: "empty" };
  }

  const { idColumn, showsTable } = bandEntry;
  const positionColumn = band === "phish" ? "position" : "song_position";
  const setlistTable = `${band}_setlists_raw`;

  const { data: showRows, error: showError } = await client
    .from(showsTable)
    .select(showDetailsColumns(band, idColumn))
    .eq("show_date", showDate);

  if (showError) {
    console.error(`Setlist show lookup failed (${band} ${showDate}):`, showError);
    return { status: "error" };
  }

  const normalizedShowRows = filterExcludedShows(
    band,
    (showRows ?? [])
      .map((item) => asRecord(item))
      .filter((item): item is Record<string, unknown> => item !== null),
    idColumn,
  );
  const showIds = normalizedShowRows
    .map((row) => row[idColumn])
    .filter(
      (value): value is string | number =>
        value !== undefined && value !== null,
    );

  if (showIds.length === 0) {
    return { status: "empty" };
  }

  const sortColumn = band === "um" ? "set_sequence" : "set_number";
  const setlistResponse = await client
    .from(setlistTable)
    .select(buildSetlistSelectColumns(band, idColumn, positionColumn))
    .in(idColumn, showIds)
    .order(sortColumn, { ascending: true })
    .order(positionColumn, { ascending: true });

  if (setlistResponse.error) {
    console.error(
      `Setlist rows lookup failed (${band} ${showDate}):`,
      setlistResponse.error,
    );
    return { status: "error" };
  }

  const rawSetlistRows = (setlistResponse.data ?? [])
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null);

  if (rawSetlistRows.length === 0) {
    return { status: "empty" };
  }

  const matchingShowRow = pickShowWithMostSongs(
    normalizedShowRows,
    idColumn,
    countRowsByShowId(rawSetlistRows, idColumn),
  );
  const targetShowId = String(matchingShowRow?.[idColumn] ?? showIds[0]);

  const seen = new Set<string>();
  const songs: SetlistSong[] = rawSetlistRows.flatMap((row) => {
    if (String(row[idColumn] ?? targetShowId) !== targetShowId) {
      return [];
    }

    const setNumber = parseSetNumber(row);
    const position = parseNumber(row[positionColumn]);
    const key = `${setNumber ?? "unknown"}-${position ?? "unknown"}-${String(row.song_name ?? "")}`;
    if (seen.has(key)) {
      return [];
    }
    seen.add(key);
    return [
      {
        setNumber,
        position,
        songName: String(row.song_name ?? "Unknown Song"),
      },
    ];
  });

  if (songs.length === 0) {
    return { status: "empty" };
  }

  return { status: "ready", setlist: { showDetails: matchingShowRow, songs } };
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
        .select(showDetailsColumns(band, bandState.bandEntry.idColumn))
        .eq("show_date", showDate);

      if (error) {
        return failedQuery("getShowDetailsByDate", error);
      }

      const { idColumn } = bandState.bandEntry;
      const candidates = filterExcludedShows(
        band,
        (data ?? [])
          .map((item) => asRecord(item))
          .filter((item): item is Record<string, unknown> => item !== null),
        idColumn,
      );

      let songCounts = new Map<string, number>();
      if (candidates.length > 1) {
        const ids = candidates.map((candidate) => candidate[idColumn] as string | number);
        const { data: countRows, error: countError } = await client
          .from(`${band}_setlists_raw`)
          .select(idColumn)
          .in(idColumn, ids);
        if (countError) {
          return failedQuery("getShowDetailsByDate song counts", countError);
        }
        songCounts = countRowsByShowId(
          (countRows ?? [])
            .map((item) => asRecord(item))
            .filter((item): item is Record<string, unknown> => item !== null),
          idColumn,
        );
      }

      const row = pickShowWithMostSongs(candidates, idColumn, songCounts);
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band,
        show: buildShowDetails(row),
      };
    } catch (error) {
      return failedQuery("getShowDetailsByDate", error);
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

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const todayIso = getEasternTodayIso();
      if (bandState.band === "um") {
        const { data: upcomingData, error: upcomingError } = await client
          .from("um_upcoming_shows")
          .select(UM_UPCOMING_SHOW_COLUMNS)
          .gte("starts_at_local", todayIso)
          .order("starts_at_local", { ascending: true })
          .order("starts_at", { ascending: true })
          .limit(25);

        if (upcomingError) {
          return failedQuery("getNextShowDetails (um upcoming)", upcomingError);
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
        .select(showDetailsColumns(bandState.band, bandState.bandEntry.idColumn))
        .gte("show_date", todayIso)
        .order("show_date", { ascending: true })
        .limit(1);

      if (error) {
        return failedQuery("getNextShowDetails", error);
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
      return failedQuery("getNextShowDetails", error);
    }
  },
);

// How many recent past show dates to scan for one that has a setlist.
const LAST_SHOW_LOOKBACK_DATES = 10;

type LastShowData = {
  band: BandSlug;
  setlist: SetlistSnapshot;
  /** Most recent past show date whose setlist is not published yet. */
  pendingShowDate: string | null;
};

export const getLastShowSetlist = cache(
  async (bandInput: string | undefined): Promise<RouteState<LastShowData>> => {
    const missingEnv = getClientOrState<LastShowData>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<LastShowData>;
    }

    const band = bandState.band;
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { showsTable, idColumn } = bandState.bandEntry;
      const todayIso = getEasternTodayIso();

      const { data: recentShows, error } = await client
        .from(showsTable)
        .select(`${idColumn}, show_date`)
        .lt("show_date", todayIso)
        .order("show_date", { ascending: false })
        .limit(LAST_SHOW_LOOKBACK_DATES * 3);

      if (error) {
        return failedQuery("getLastShowSetlist", error);
      }

      const recentDates = [
        ...new Set(
          filterExcludedShows(
            band,
            (recentShows ?? [])
              .map((item) => asRecord(item))
              .filter((item): item is Record<string, unknown> => item !== null),
            idColumn,
          )
            .map((row) => row.show_date)
            .filter((value): value is string => typeof value === "string"),
        ),
      ].slice(0, LAST_SHOW_LOOKBACK_DATES);

      let pendingShowDate: string | null = null;
      for (const showDate of recentDates) {
        const lookup = await lookupSetlistForDate(band, showDate);
        if (lookup.status === "error") {
          return { status: "error", message: "Setlist lookup failed" };
        }
        if (lookup.status === "ready") {
          return { status: "ready", band, setlist: lookup.setlist, pendingShowDate };
        }
        pendingShowDate ??= showDate;
      }

      return { status: "empty" };
    } catch (error) {
      return failedQuery("getLastShowSetlist", error);
    }
  },
);

export const getRecentMissingSetlistShows = cache(
  async (
    bandInput: string | undefined,
    latestPredictionTargetDate: string | null = null,
  ): Promise<MissingSetlistShow[]> => {
    const client = getSupabaseServerClient();
    if (!client) {
      return [];
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return [];
    }

    const { band, bandEntry } = bandState;
    const { showsTable, idColumn } = bandEntry;
    const setlistTable = `${band}_setlists_raw`;
    const now = new Date();
    const todayIso = getEasternTodayIso(now);
    const cutoffIso = getEasternDateOffsetIso(-7, now);

    try {
      const { data: showData, error: showError } = await client
        .from(showsTable)
        .select(showDetailsColumns(band, idColumn))
        .gte("show_date", cutoffIso)
        .lt("show_date", todayIso)
        .order("show_date", { ascending: true });

      if (showError) {
        console.error("getRecentMissingSetlistShows show query failed:", showError);
        return [];
      }
      if (!showData || showData.length === 0) {
        return [];
      }

      const showRows = showData
        .map((item) => asRecord(item))
        .filter((item): item is Record<string, unknown> => item !== null);

      const showIds = showRows
        .map((row) => row[idColumn] ?? row.show_id)
        .filter((value): value is string | number => value !== undefined && value !== null);

      if (showIds.length === 0) {
        return [];
      }

      const { data: setlistData, error: setlistError } = await client
        .from(setlistTable)
        .select(`${idColumn}, song_name`)
        .in(idColumn, showIds);

      if (setlistError) {
        console.error("getRecentMissingSetlistShows setlist query failed:", setlistError);
        return [];
      }

      const setlistRows = (setlistData ?? [])
        .map((item) => asRecord(item))
        .filter((item): item is Record<string, unknown> => item !== null);

      return findMissingSetlistShows(band, showRows, setlistRows, {
        idColumn,
        now,
        latestPredictionTargetDate,
      });
    } catch (error) {
      console.error("getRecentMissingSetlistShows failed:", error);
      return [];
    }
  },
);
