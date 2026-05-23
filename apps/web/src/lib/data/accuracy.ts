import "server-only";

import { cache } from "react";

import type { BandSlug } from "@/lib/config";
import { getSupabaseServerClient, getServiceRoleClient } from "@/lib/supabase/server";
import { getEasternTodayIso } from "@/lib/show-status";

import { getClientOrState, getBandContext } from "./bands";
import {
  asRecord,
  parseNumber,
  getVenueNameFromRow,
  getVenueCityFromRow,
  getVenueRegionFromRow,
} from "./parsers";
import type { AccuracyRow, RouteState } from "./types";

const MIN_COMPLETE_SETLIST_SONGS = 3;

function getAccuracyRowKey(row: AccuracyRow) {
  if (row.showId) {
    return row.showId;
  }

  if (!row.showDate) {
    return null;
  }

  return [row.showDate, row.venueName ?? "", row.city ?? "", row.state ?? ""].join("|");
}

async function getLatestPredictionModelVersion(
  client: NonNullable<ReturnType<typeof getSupabaseServerClient>>,
  band: string,
) {
  const { data, error } = await client
    .from("setlist_predictions")
    .select("model_version")
    .eq("band", band)
    .order("generated_at", { ascending: false })
    .limit(1);

  if (error) {
    throw new Error(error.message);
  }

  const modelVersion = data?.[0]?.model_version;
  return typeof modelVersion === "string" && modelVersion.length > 0
    ? modelVersion
    : null;
}

export const getRecentAccuracy = cache(
  async (
    bandInput: string | undefined,
    limit = 25,
  ): Promise<RouteState<{ band: BandSlug; rows: AccuracyRow[] }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      rows: AccuracyRow[];
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        rows: AccuracyRow[];
      }>;
    }

    const band = bandState.band;
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const modelVersion = await getLatestPredictionModelVersion(client, band);
      const easternToday = getEasternTodayIso();
      let query = client
        .from("setlist_accuracy")
        .select(
          "show_id, show_date, p10, p25, p50, recall_10, recall_25, recall_50, actual_song_count, weighted_precision_score",
        )
        .eq("band", band)
        .gte("actual_song_count", MIN_COMPLETE_SETLIST_SONGS)
        .lt("show_date", easternToday)
        .order("show_date", { ascending: false });

      if (modelVersion) {
        query = query.eq("model_version", modelVersion);
      }

      const { data, error } = await query.limit(limit);

      if (error) {
        return { status: "error", message: error.message };
      }

      const accuracyRows =
        data?.map((row) => ({
          showId:
            typeof row.show_id === "string" || typeof row.show_id === "number"
              ? String(row.show_id)
              : null,
          showDate: typeof row.show_date === "string" ? row.show_date : null,
          recall10: parseNumber(row.recall_10),
          recall25: parseNumber(row.recall_25),
          recall50: parseNumber(row.recall_50),
          p10: parseNumber(row.p10),
          p25: parseNumber(row.p25),
          p50: parseNumber(row.p50),
          actualSongCount: parseNumber(row.actual_song_count),
          weightedPrecisionScore: parseNumber(row.weighted_precision_score),
        })) ?? [];

      if (accuracyRows.length === 0) {
        return { status: "empty" };
      }

      const { idColumn, showsTable } = bandState.bandEntry;
      const showIds = [...new Set(accuracyRows.map((row) => row.showId).filter(Boolean))];
      const showDates = [...new Set(accuracyRows.map((row) => row.showDate).filter(Boolean))];
      const showMetaByShowId = new Map<
        string,
        { venueName: string | null; city: string | null; state: string | null }
      >();
      const showMetaByShowDate = new Map<
        string,
        { venueName: string | null; city: string | null; state: string | null }
      >();

      if (showIds.length > 0 && showsTable && idColumn) {
        const showClient = getServiceRoleClient() ?? client;
        const { data: showData, error: showError } = await showClient
          .from(showsTable)
          .select("*")
          .in(idColumn, showIds);

        if (showError) {
          console.error("accuracy: show metadata lookup failed (id path)", showError);
        } else {
          for (const item of showData ?? []) {
            const row = asRecord(item);
            if (!row) {
              continue;
            }

            const showMeta = {
              venueName: getVenueNameFromRow(row),
              city: getVenueCityFromRow(row),
              state: getVenueRegionFromRow(row),
            };
            const showIdValue = row[idColumn];
            if (typeof showIdValue === "string" || typeof showIdValue === "number") {
              showMetaByShowId.set(String(showIdValue), showMeta);
            }

            if (typeof row.show_date === "string") {
              showMetaByShowDate.set(row.show_date, showMeta);
            }
          }
        }
      }

      if (showMetaByShowId.size === 0 && showDates.length > 0 && showsTable) {
        const { data: showData, error: showError } = await client
          .from(showsTable)
          .select("*")
          .in("show_date", showDates);

        if (showError) {
          console.error("accuracy: show metadata lookup failed (date path)", {
            band, showsTable, error: showError.message,
          });
        } else {
          for (const item of showData ?? []) {
            const row = asRecord(item);
            if (!row || typeof row.show_date !== "string") {
              continue;
            }

            showMetaByShowDate.set(row.show_date, {
              venueName: getVenueNameFromRow(row),
              city: getVenueCityFromRow(row),
              state: getVenueRegionFromRow(row),
            });
          }
        }
      }

      const rows: AccuracyRow[] = accuracyRows.map((row) => ({
        ...(row.showId ? showMetaByShowId.get(row.showId) : null) ??
          (row.showDate ? showMetaByShowDate.get(row.showDate) : null) ?? {
            venueName: null,
            city: null,
            state: null,
          },
        showId: row.showId,
        showDate: row.showDate,
        recall10: row.recall10,
        recall25: row.recall25,
        recall50: row.recall50,
        p10: row.p10,
        p25: row.p25,
        p50: row.p50,
        actualSongCount: row.actualSongCount,
        weightedPrecisionScore: row.weightedPrecisionScore,
      }));

      const uniqueRows = rows.filter((row, index, allRows) => {
        const key = getAccuracyRowKey(row);
        if (!key) {
          return true;
        }

        return allRows.findIndex((candidate) => getAccuracyRowKey(candidate) === key) === index;
      });

      const limitedRows = uniqueRows.slice(0, limit);

      return limitedRows.length === 0
        ? { status: "empty" }
        : { status: "ready", band, rows: limitedRows };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);
