/**
 * Prediction data fetching — latest, by-date, available dates, and projections.
 */

import "server-only";

import { cache } from "react";
import type { SupabaseClient } from "@supabase/supabase-js";

import {
  ACTIVE_MODELS,
  type BandSlug,
  type ModelSlug,
  normalizeModel,
} from "@/lib/config";
import { getSupabaseServerClient } from "@/lib/supabase/server";
import { selectLivePredictionSeedRow } from "@/lib/prediction-selection";

import { getClientOrState, getBandContext } from "./bands";
import {
  asRecord,
  buildPredictionSnapshotFromCanonicalRow,
  buildPredictionSnapshotFromProjectionRows,
} from "./parsers";
import type {
  PredictionSnapshot,
  ProjectionRow,
  RouteState,
  ExplorerSnapshot,
} from "./types";
import { getSetlistForDate } from "./shows";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function fetchProjectedPredictionSnapshot(
  client: SupabaseClient,
  {
    band,
    model,
    referenceDate,
  }: {
    band: BandSlug;
    model: ModelSlug;
    referenceDate?: string;
  },
): Promise<PredictionSnapshot | null> {
  let seedQuery = client
    .from("prediction_songs")
    .select("reference_date, predicted_at, model_version")
    .eq("band", band)
    .eq("model_slug", model)
    .eq("rank", 1);

  if (referenceDate) {
    seedQuery = seedQuery.eq("reference_date", referenceDate);
  }

  const { data: seedRows, error: seedError } = await seedQuery
    .order("predicted_at", { ascending: false })
    .order("reference_date", { ascending: false })
    .limit(referenceDate ? 1 : 100);

  if (seedError) {
    throw seedError;
  }

  const seedRow = referenceDate
    ? asRecord(seedRows?.[0])
    : selectLivePredictionSeedRow(
        (seedRows ?? [])
          .map((item) => asRecord(item))
          .filter((item): item is Record<string, unknown> => item !== null)
          .map((row) => ({
            reference_date:
              typeof row.reference_date === "string" ? row.reference_date : null,
            predicted_at:
              typeof row.predicted_at === "string" ? row.predicted_at : null,
            model_version:
              typeof row.model_version === "string" ? row.model_version : null,
          })),
        { todayIso: new Date().toISOString().slice(0, 10) },
      );
  const seedReferenceDate =
    seedRow && typeof seedRow.reference_date === "string"
      ? seedRow.reference_date
      : null;
  const seedModelVersion =
    seedRow && typeof seedRow.model_version === "string"
      ? seedRow.model_version
      : null;

  if (!seedReferenceDate || !seedModelVersion) {
    return null;
  }

  const { data, error } = await client
    .from("prediction_songs")
    .select(
      "reference_date, predicted_at, model_version, rank, song_name, prediction_payload",
    )
    .eq("band", band)
    .eq("model_slug", model)
    .eq("reference_date", seedReferenceDate)
    .eq("model_version", seedModelVersion)
    .order("rank", { ascending: true });

  if (error) {
    throw error;
  }

  const rows = (data ?? [])
    .map((item) => asRecord(item))
    .filter((item): item is ProjectionRow => item !== null);

  if (rows.length === 0) {
    return null;
  }

  return buildPredictionSnapshotFromProjectionRows(rows);
}

export async function getCurrentModelVersion(
  client: SupabaseClient,
  band: BandSlug,
  model: ModelSlug,
): Promise<string> {
  try {
    const projectionSnapshot = await fetchProjectedPredictionSnapshot(client, {
      band,
      model,
    });
    if (projectionSnapshot?.modelVersion) {
      return projectionSnapshot.modelVersion;
    }
  } catch (error) {
    console.error("Failed to resolve model version from prediction_songs", error);
  }

  const { data } = await client
    .from("predictions")
    .select("model_version")
    .eq("band", band)
    .eq("model_slug", model)
    .order("predicted_at", { ascending: false })
    .order("reference_date", { ascending: false })
    .limit(1);

  const row = asRecord(data?.[0]);
  if (row && typeof row.model_version === "string") {
    return row.model_version;
  }

  return `${model}_v1`;
}

export function resolveReplayModels(
  modelAInput: string | undefined,
  modelBInput: string | undefined,
): [ModelSlug, ModelSlug] {
  const modelA = ACTIVE_MODELS.includes(modelAInput as ModelSlug)
    ? (modelAInput as ModelSlug)
    : (ACTIVE_MODELS[0] ?? "notebook");
  const fallbackModelB =
    ACTIVE_MODELS.find((item) => item !== modelA) ?? ACTIVE_MODELS[0] ?? modelA;
  const requestedModelB = ACTIVE_MODELS.includes(modelBInput as ModelSlug)
    ? (modelBInput as ModelSlug)
    : fallbackModelB;
  const modelB =
    requestedModelB === modelA && ACTIVE_MODELS.length > 1
      ? fallbackModelB
      : requestedModelB;
  return [modelA, modelB];
}

// ---------------------------------------------------------------------------
// Public cached fetchers
// ---------------------------------------------------------------------------

export const getLatestPredictions = cache(
  async (
    bandInput: string | undefined,
    modelInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; snapshot: PredictionSnapshot }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      snapshot: PredictionSnapshot;
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        snapshot: PredictionSnapshot;
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      try {
        const projectionSnapshot = await fetchProjectedPredictionSnapshot(client, {
          band,
          model,
        });
        if (projectionSnapshot) {
          return { status: "ready", band, model, snapshot: projectionSnapshot };
        }
      } catch (error) {
        console.error("Failed to load latest projected predictions", error);
      }

      const { data, error } = await client
        .from("predictions")
        .select("*")
        .eq("band", band)
        .eq("model_slug", model)
        .order("reference_date", { ascending: false })
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
        model,
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
    modelInput: string | undefined,
    referenceDate: string,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; snapshot: PredictionSnapshot }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      snapshot: PredictionSnapshot;
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        snapshot: PredictionSnapshot;
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      try {
        const projectionSnapshot = await fetchProjectedPredictionSnapshot(client, {
          band,
          model,
          referenceDate,
        });
        if (projectionSnapshot) {
          return { status: "ready", band, model, snapshot: projectionSnapshot };
        }
      } catch (error) {
        console.error("Failed to load projected predictions for date", error);
      }

      const { data, error } = await client
        .from("predictions")
        .select("*")
        .eq("band", band)
        .eq("model_slug", model)
        .eq("reference_date", referenceDate)
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
        model,
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
    modelInput: string | undefined,
  ): Promise<RouteState<{ band: BandSlug; model: ModelSlug; dates: string[] }>> => {
    const missingEnv = getClientOrState<{
      band: BandSlug;
      model: ModelSlug;
      dates: string[];
    }>();
    if (missingEnv) {
      return missingEnv;
    }

    const bandState = await getBandContext(bandInput);
    if (bandState.status !== "ready") {
      return bandState as RouteState<{
        band: BandSlug;
        model: ModelSlug;
        dates: string[];
      }>;
    }

    const band = bandState.band;
    const model = normalizeModel(modelInput);
    const client = getSupabaseServerClient();

    if (!client) {
      return { status: "missing_env" };
    }

    try {
      let dates: string[] = [];

      try {
        const { data: projectionData, error: projectionError } = await client
          .from("prediction_songs")
          .select("reference_date")
          .eq("band", band)
          .eq("model_slug", model)
          .order("reference_date", { ascending: false })
          .limit(100);

        if (!projectionError && projectionData && projectionData.length > 0) {
          dates = [...new Set(
            projectionData
              .map((row) => asRecord(row)?.reference_date)
              .filter((d): d is string => typeof d === "string")
          )];
        }
      } catch {
      }

      if (dates.length === 0) {
        const { data, error } = await client
          .from("predictions")
          .select("reference_date")
          .eq("band", band)
          .eq("model_slug", model)
          .order("reference_date", { ascending: false })
          .limit(100);

        if (error) {
          return { status: "error", message: error.message };
        }

        dates = [...new Set(
          (data ?? [])
            .map((row) => asRecord(row)?.reference_date)
            .filter((d): d is string => typeof d === "string")
        )];
      }

      return dates.length === 0
        ? { status: "empty" }
        : { status: "ready", band, model, dates };
    } catch (error) {
      return {
        status: "error",
        message: error instanceof Error ? error.message : "Unknown error",
      };
    }
  },
);

export async function getExplorerSnapshot(
  bandInput: string | undefined,
  modelInput: string | undefined,
  selectedDateInput?: string,
): Promise<RouteState<{ band: BandSlug; model: ModelSlug; explorer: ExplorerSnapshot }>> {
  const datesState = await getPredictionDates(bandInput, modelInput);

  if (datesState.status !== "ready") {
    return datesState as RouteState<{
      band: BandSlug;
      model: ModelSlug;
      explorer: ExplorerSnapshot;
    }>;
  }

  const selectedDate =
    selectedDateInput && datesState.dates.includes(selectedDateInput)
      ? selectedDateInput
      : datesState.dates[0] ?? null;
  if (!selectedDate) {
    return { status: "empty" };
  }

  const [predictionsState, setlist] = await Promise.all([
    getPredictionsForDate(datesState.band, datesState.model, selectedDate),
    getSetlistForDate(datesState.band, selectedDate),
  ]);

  if (predictionsState.status !== "ready") {
    return predictionsState as RouteState<{
      band: BandSlug;
      model: ModelSlug;
      explorer: ExplorerSnapshot;
    }>;
  }

  return {
    status: "ready",
    band: datesState.band,
    model: datesState.model,
    explorer: {
      availableDates: datesState.dates,
      selectedDate,
      predictions: predictionsState.snapshot,
      setlist,
    },
  };
}
