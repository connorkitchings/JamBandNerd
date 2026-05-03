/**
 * Replay data fetching — historical prediction comparison across models.
 */

import "server-only";

import { cache } from "react";

import type { BandSlug, ModelSlug } from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { buildShowDetails } from "@/lib/next-show";

import { getClientOrState, getBandContext } from "./bands";
import { getPreviewReplaySnapshot, shouldUseLocalPreview } from "./preview";
import {
  asRecord,
  getVenueNameFromRow,
  buildPredictionSnapshotFromCanonicalRow,
} from "./parsers";
import { getCurrentModelVersion, resolveReplayModels } from "./predictions";
import { getSetlistForDate, buildFallbackSetlistFromHistoricalRow } from "./shows";
import type { PredictionSnapshot, ReplaySnapshot, RouteState } from "./types";

export const getReplaySnapshot = cache(
  async (
    bandInput: string | undefined,
    selectedDateInput?: string,
    modelAInput?: string,
    modelBInput?: string,
    replayWindow = 50,
  ): Promise<RouteState<{ band: BandSlug; replay: ReplaySnapshot }>> => {
    const missingEnv = getClientOrState<{ band: BandSlug; replay: ReplaySnapshot }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{ band: BandSlug; replay: ReplaySnapshot }>;
    }

    if (shouldUseLocalPreview()) {
      return getPreviewReplaySnapshot(
        bandInput,
        selectedDateInput,
        modelAInput,
        modelBInput,
        replayWindow,
      );
    }

    const client = getSupabaseServerClient();
    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const band = bandState.band;
      const { showsTable } = bandState.bandEntry;
      const [modelA, modelB] = resolveReplayModels(modelAInput, modelBInput);
      const modelVersions = await Promise.all(
        [modelA, modelB].map(async (model) => ({
          model,
          version: await getCurrentModelVersion(client, band, model),
        })),
      );

      const historicalRowsByModel = await Promise.all(
        modelVersions.map(async ({ model, version }) => {
          const { data, error } = await client
            .from("completed_show_prediction_runs")
            .select("target_show_date, generated_at")
            .eq("band", band)
            .eq("model_slug", model)
            .eq("model_version", version)
            .order("target_show_date", { ascending: false })
            .order("generated_at", { ascending: false })
            .limit(Math.max(replayWindow * 4, 100));

          if (error) {
            throw new Error(error.message);
          }

          const dedupedDates: string[] = [];
          const seen = new Set<string>();
          for (const item of data ?? []) {
            const row = asRecord(item);
            const showDate =
              row && typeof row.target_show_date === "string"
                ? row.target_show_date
                : null;
            if (!showDate || seen.has(showDate)) {
              continue;
            }
            seen.add(showDate);
            dedupedDates.push(showDate);
          }

          return { model, dates: dedupedDates };
        }),
      );

      const replayableDateSet = historicalRowsByModel.reduce<Set<string> | null>(
        (shared, entry) => {
          const dates = new Set(entry.dates);
          if (!shared) {
            return dates;
          }

          return new Set([...shared].filter((date) => dates.has(date)));
        },
        null,
      );

      const availableDates = [...(replayableDateSet ?? new Set<string>())]
        .sort((left, right) => right.localeCompare(left))
        .slice(0, replayWindow);

      if (availableDates.length === 0) {
        return { status: "empty" };
      }

      const selectedDate =
        selectedDateInput && availableDates.includes(selectedDateInput)
          ? selectedDateInput
          : availableDates[0] ?? null;

      if (!selectedDate) {
        return { status: "empty" };
      }

      const { data: showRows, error: showError } = await client
        .from(showsTable)
        .select("*")
        .in("show_date", availableDates);

      if (showError) {
        return { status: "error", message: showError.message };
      }

      const showByDate = new Map<string, Record<string, unknown>>();
      for (const item of showRows ?? []) {
        const row = asRecord(item);
        if (!row || typeof row.show_date !== "string") {
          continue;
        }
        showByDate.set(row.show_date, row);
      }

      const availableShows = availableDates.map((showDate) => ({
        showDate,
        venueName: getVenueNameFromRow(showByDate.get(showDate) ?? null),
      }));

      const historicalSnapshots = await Promise.all(
        modelVersions.map(async ({ model, version }) => {
          const { data, error } = await client
            .from("completed_show_prediction_runs")
            .select("*")
            .eq("band", band)
            .eq("model_slug", model)
            .eq("model_version", version)
            .eq("target_show_date", selectedDate)
            .order("generated_at", { ascending: false })
            .limit(1);

          if (error) {
            throw new Error(error.message);
          }

          const row = asRecord(data?.[0]);
          return {
            model,
            row,
            snapshot: row ? buildPredictionSnapshotFromCanonicalRow(row) : null,
          };
        }),
      );

      const snapshots = historicalSnapshots.reduce<Partial<Record<ModelSlug, PredictionSnapshot | null>>>(
        (acc, entry) => {
          acc[entry.model] = entry.snapshot;
          return acc;
        },
        {},
      );

      const setlist =
        (await getSetlistForDate(band, selectedDate)) ??
        buildFallbackSetlistFromHistoricalRow(
          historicalSnapshots.find((entry) => entry.row)?.row ?? null,
        );

      const selectedShow = showByDate.get(selectedDate) ?? null;

      return {
        status: "ready",
        band,
        replay: {
          availableShows,
          selectedDate,
          show: selectedShow ? buildShowDetails(selectedShow) : null,
          setlist,
          modelA,
          modelB,
          snapshots,
        },
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);
