/**
 * Accuracy data fetching — per-show recall and precision metrics.
 */

import "server-only";

import { cache } from "react";

import type { BandSlug, ModelSlug } from "@/lib/config";
import { normalizeModel } from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";

import { getClientOrState, getBandContext } from "./bands";
import {
  asRecord,
  parseNumber,
  getVenueNameFromRow,
  getVenueCityFromRow,
  getVenueRegionFromRow,
} from "./parsers";
import { getCurrentModelVersion } from "./predictions";
import type { AccuracyRow, RouteState } from "./types";

export const getRecentAccuracy = cache(
  async (
    bandInput: string | undefined,
    modelInput: string | undefined,
    limit = 25,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; rows: AccuracyRow[] }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      rows: AccuracyRow[];
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        rows: AccuracyRow[];
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const modelVersion = await getCurrentModelVersion(client, band, model);
      const { data, error } = await client
        .from("completed_show_accuracy")
        .select("show_id, show_date, k10_recall, k25_recall, k50_recall, k10_precision, k25_precision, k50_precision")
        .eq("band", band)
        .eq("model_slug", model)
        .eq("model_version", modelVersion)
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
          k10Recall: parseNumber(row.k10_recall),
          k25Recall: parseNumber(row.k25_recall),
          k50Recall: parseNumber(row.k50_recall),
          k10Precision: parseNumber(row.k10_precision),
          k25Precision: parseNumber(row.k25_precision),
          k50Precision: parseNumber(row.k50_precision),
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
        k10Recall: row.k10Recall,
        k25Recall: row.k25Recall,
        k50Recall: row.k50Recall,
        k10Precision: row.k10Precision,
        k25Precision: row.k25Precision,
        k50Precision: row.k50Precision,
      }));

      return rows.length === 0
        ? { status: "empty" }
        : { status: "ready", band, model, rows };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);
