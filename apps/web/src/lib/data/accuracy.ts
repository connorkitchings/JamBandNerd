import "server-only";

import { cache } from "react";

import type { BandSlug } from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";

import { getClientOrState, getBandContext } from "./bands";
import {
  asRecord,
  parseNumber,
  getVenueNameFromRow,
  getVenueCityFromRow,
  getVenueRegionFromRow,
} from "./parsers";
import type { AccuracyRow, RouteState } from "./types";

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
      const { data, error } = await client
        .from("setlist_accuracy")
        .select(
          "show_id, show_date, p10, p25, p50, recall_10, recall_25, recall_50, weighted_precision_score",
        )
        .eq("band", band)
        .order("show_date", { ascending: false })
        .limit(limit);

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

      if (showIds.length > 0) {
        const { data: showData, error: showError } = await client
          .from(showsTable)
          .select("*")
          .in(idColumn, showIds);

        if (showError) {
          return { status: "error", message: showError.message };
        }

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
      } else if (showDates.length > 0) {
        const { data: showData, error: showError } = await client
          .from(showsTable)
          .select("*")
          .in("show_date", showDates);

        if (showError) {
          return { status: "error", message: showError.message };
        }

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

      const rows: AccuracyRow[] = accuracyRows.map((row) => ({
        ...(row.showId ? showMetaByShowId.get(row.showId) : null) ??
          (row.showDate ? showMetaByShowDate.get(row.showDate) : null) ?? {
            venueName: null,
            city: null,
            state: null,
          },
        showDate: row.showDate,
        recall10: row.recall10,
        recall25: row.recall25,
        recall50: row.recall50,
        p10: row.p10,
        p25: row.p25,
        p50: row.p50,
        weightedPrecisionScore: row.weightedPrecisionScore,
      }));

      return rows.length === 0
        ? { status: "empty" }
        : { status: "ready", band, rows };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);
