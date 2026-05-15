import "server-only";

import { cache } from "react";

import type { BandSlug } from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { selectLivePredictionSeedRow } from "@/lib/prediction-selection";
import { getEasternTodayIso } from "@/lib/show-status";

import { getClientOrState, getBandContext } from "./bands";
import { asRecord, buildPredictionSnapshotFromCanonicalRow } from "./parsers";
import type { PredictionSnapshot, RouteState } from "./types";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function toSeedRows(data: unknown[]) {
  return data
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map((row) => ({
      reference_date:
        typeof row.reference_date === "string" ? row.reference_date : null,
      target_show_date:
        typeof row.target_show_date === "string" ? row.target_show_date : null,
      target_show_key:
        typeof row.target_show_key === "string" ? row.target_show_key : null,
      predicted_at:
        typeof row.generated_at === "string"
          ? row.generated_at
          : null,
      model_version:
        typeof row.model_version === "string" ? row.model_version : null,
    }));
}

// ---------------------------------------------------------------------------
// Public cached fetchers
// ---------------------------------------------------------------------------

export const getLatestPredictions = cache(
  async (
    bandInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; snapshot: PredictionSnapshot }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      snapshot: PredictionSnapshot;
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        snapshot: PredictionSnapshot;
      }>;
    }

    const band = bandState.band;
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { data: seedRows, error: seedError } = await client
        .from("setlist_predictions")
        .select(
          "reference_date, target_show_date, generated_at, model_version, target_show_key",
        )
        .eq("band", band)
        .order("generated_at", { ascending: false })
        .limit(100);

      if (seedError) {
        return { status: "error", message: seedError.message };
      }

      const seedRow = selectLivePredictionSeedRow(toSeedRows(seedRows ?? []), {
        todayIso: getEasternTodayIso(),
      });

      if (!seedRow?.model_version || !seedRow.target_show_key) {
        return { status: "empty" };
      }

      const matchedSeed = (seedRows ?? []).find(
        (r) =>
          r.target_show_key === seedRow.target_show_key &&
          r.model_version === seedRow.model_version,
      );

      if (!matchedSeed?.target_show_key) {
        return { status: "empty" };
      }

      const { data, error } = await client
        .from("setlist_predictions")
        .select("*")
        .eq("band", band)
        .eq("model_version", matchedSeed.model_version)
        .eq("target_show_key", matchedSeed.target_show_key)
        .limit(1);

      if (error) {
        return { status: "error", message: error.message };
      }

      const row = data?.[0];
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band,
        snapshot: buildPredictionSnapshotFromCanonicalRow(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getPredictionsForDate = cache(
  async (
    bandInput: string | undefined,
    targetShowDate: string,
  ): Promise<RouteState<{ band: BandSlug; snapshot: PredictionSnapshot }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      snapshot: PredictionSnapshot;
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        snapshot: PredictionSnapshot;
      }>;
    }

    const band = bandState.band;
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { data: resultData, error: resultError } = await client
        .from("setlist_results")
        .select("*")
        .eq("band", band)
        .eq("target_show_date", targetShowDate)
        .order("generated_at", { ascending: false })
        .limit(1);

      if (resultError) {
        return { status: "error", message: resultError.message };
      }

      let row = resultData?.[0];
      if (!row) {
        const { data: liveData, error: liveError } = await client
          .from("setlist_predictions")
          .select("*")
          .eq("band", band)
          .eq("target_show_date", targetShowDate)
          .order("generated_at", { ascending: false })
          .limit(1);

        if (liveError) {
          return { status: "error", message: liveError.message };
        }

        row = liveData?.[0];
      }
      if (!row) {
        return { status: "empty" };
      }

      return {
        status: "ready",
        band,
        snapshot: buildPredictionSnapshotFromCanonicalRow(row),
      };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export const getPredictionDates = cache(
  async (
    bandInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; dates: string[] }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      dates: string[];
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        dates: string[];
      }>;
    }

    const band = bandState.band;
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      const { data, error } = await client
        .from("setlist_predictions")
        .select("reference_date, target_show_date, target_show_key")
        .eq("band", band)
        .order("target_show_date", { ascending: false })
        .limit(200);

      if (error) {
        return { status: "error", message: error.message };
      }

      const dates = [
        ...new Set(
          (data ?? [])
            .map((row) => asRecord(row)?.target_show_date)
            .filter((d): d is string => typeof d === "string"),
        ),
      ];

      return dates.length === 0
        ? { status: "empty" }
        : { status: "ready", band, dates };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);
