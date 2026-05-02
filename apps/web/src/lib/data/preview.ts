import { ACTIVE_MODELS, type BandSlug, type ModelSlug, normalizeModel } from "@/lib/config";
import type { BandEntry, AccuracyRow, ExplorerSnapshot, PredictionRow, PredictionSnapshot, ReplayShowOption, ReplaySnapshot, RouteState, SetlistSnapshot, ShowDetails } from "./types";
import { computeTier } from "./parsers";

const PREVIEW_BAND_SLUGS = ["goose", "phish", "wsp", "billy"] as const;

type PreviewBandSlug = (typeof PREVIEW_BAND_SLUGS)[number];

type PredictionInput = Omit<PredictionRow, "rank" | "tier">;

type PreviewShowInput = {
  showDate: string;
  venueName: string;
  city: string;
  state: string;
  country?: string;
};

type PreviewBandConfig = {
  band: BandEntry;
  nextShow: ShowDetails;
  latestShowDate: string;
  lastShowDate: string;
  predictionDates: string[];
  latestSnapshots: Partial<Record<ModelSlug, PredictionSnapshot>>;
  snapshotsByDate: Record<string, Partial<Record<ModelSlug, PredictionSnapshot>>>;
  accuracyByModel: Partial<Record<ModelSlug, AccuracyRow[]>>;
  showDetailsByDate: Record<string, ShowDetails>;
  setlistsByDate: Record<string, SetlistSnapshot>;
  replayAvailableShows: ReplayShowOption[];
  replaySelectedDate: string;
};

type PreviewPredictionWindow = {
  targetShowDate: string;
  referenceDate: string;
  predictedAt: string;
  modelVersions: Partial<Record<ModelSlug, string>>;
  rowsByModel: Partial<Record<ModelSlug, PredictionInput[]>>;
};

function makeShowDetails(input: PreviewShowInput): ShowDetails {
  const raw = {
    venue_name: input.venueName,
    venue_city: input.city,
    venue_state: input.state,
    venue_country: input.country ?? "USA",
    show_date: input.showDate,
  };

  return {
    venueName: input.venueName,
    city: input.city,
    state: input.state,
    country: input.country ?? "USA",
    showDate: input.showDate,
    raw,
  };
}

function makeSetlistSnapshot(
  showDetails: ShowDetails,
  songs: string[],
): SetlistSnapshot {
  return {
    showDetails: showDetails.raw,
    songs: songs.map((songName, index) => ({
      setNumber: index < 6 ? 1 : 2,
      position: index + 1,
      songName,
    })),
  };
}

function makePredictionRows(rows: PredictionInput[]): PredictionRow[] {
  return rows.map((row, index) => ({
    ...row,
    rank: index + 1,
    tier: computeTier(index + 1),
  }));
}

function makePredictionSnapshot(
  band: BandEntry,
  model: ModelSlug,
  window: PreviewPredictionWindow,
): PredictionSnapshot {
  const rows = makePredictionRows(window.rowsByModel[model] ?? window.rowsByModel.notebook ?? []);

  return {
    targetShowDate: window.targetShowDate,
    referenceDate: window.referenceDate,
    predictedAt: window.predictedAt,
    modelVersion:
      window.modelVersions[model] ??
      window.modelVersions.notebook ??
      `${model}_preview_v1`,
    predictions: rows,
    raw: {
      source: "local-preview",
      band: band.slug,
      model,
      targetShowDate: window.targetShowDate,
      referenceDate: window.referenceDate,
      predictedAt: window.predictedAt,
    },
  };
}

function row(
  songName: string,
  probability: number,
  currentGap: number | null,
  recentPlays50: number | null,
  playsPastYear: number | null,
  lastPlayed: string | null,
  extras: Partial<PredictionRow> = {},
): PredictionInput {
  return {
    songName,
    probability,
    currentGap,
    recentPlays50,
    playsPastYear,
    lastPlayed,
    avgGap: extras.avgGap ?? currentGap,
    recentAvgGap: extras.recentAvgGap ?? currentGap,
    gapRatio: extras.gapRatio ?? null,
    gapZScore: extras.gapZScore ?? null,
    ckplusScore: extras.ckplusScore ?? probability * 10,
  };
}

function makeAccuracyRows(
  rows: Array<{
    showDate: string;
    venueName: string;
    city: string;
    state: string;
    k10Recall: number;
    k25Recall: number;
    k50Recall: number;
    k10Precision: number;
    k25Precision: number;
    k50Precision: number;
  }>,
): AccuracyRow[] {
  return rows.map((row) => ({
    showDate: row.showDate,
    venueName: row.venueName,
    city: row.city,
    state: row.state,
    k10Recall: row.k10Recall,
    k25Recall: row.k25Recall,
    k50Recall: row.k50Recall,
    k10Precision: row.k10Precision,
    k25Precision: row.k25Precision,
    k50Precision: row.k50Precision,
  }));
}

function resolvePreviewReplayModels(
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
    requestedModelB === modelA && ACTIVE_MODELS.length > 1 ? fallbackModelB : requestedModelB;
  return [modelA, modelB];
}

function makeBandPreview(config: {
  slug: PreviewBandSlug;
  displayName: string;
  nextShow: PreviewShowInput;
  lastShow: PreviewShowInput;
  replayShow: PreviewShowInput;
  latestTargetDate: string;
  predictionDates: string[];
  latestPredictedAt: string;
  latestModelVersions: Partial<Record<ModelSlug, string>>;
  latestRowsByModel: Partial<Record<ModelSlug, PredictionInput[]>>;
  historicalWindows: Array<PreviewPredictionWindow & { show: PreviewShowInput }>;
  accuracyRowsByModel: Partial<Record<ModelSlug, AccuracyRow[]>>;
  replaySongs: string[];
}) {
  const band: BandEntry = {
    slug: config.slug,
    displayName: config.displayName,
    showsTable: `${config.slug}_shows`,
    idColumn: `${config.slug}_show_id`,
  };

  const nextShow = makeShowDetails(config.nextShow);
  const lastShow = makeShowDetails(config.lastShow);
  const replayShow = makeShowDetails(config.replayShow);

  const showDetailsByDate: Record<string, ShowDetails> = {
    [config.nextShow.showDate]: nextShow,
    [config.lastShow.showDate]: lastShow,
    [config.replayShow.showDate]: replayShow,
  };

  const setlistsByDate: Record<string, SetlistSnapshot> = {
    [config.lastShow.showDate]: makeSetlistSnapshot(lastShow, config.replaySongs),
    [config.replayShow.showDate]: makeSetlistSnapshot(replayShow, config.replaySongs),
  };

  const historicalWindows: Array<PreviewPredictionWindow & { show: PreviewShowInput }> = [
    {
      show: config.lastShow,
      targetShowDate: config.lastShow.showDate,
      referenceDate: config.lastShow.showDate,
      predictedAt: config.latestPredictedAt,
      modelVersions: config.latestModelVersions,
      rowsByModel: config.latestRowsByModel,
    },
    ...config.historicalWindows,
  ];

  const predictionDates = [...new Set([
    config.latestTargetDate,
    config.lastShow.showDate,
    ...config.predictionDates,
    ...historicalWindows.map((window) => window.referenceDate),
  ])].sort((left, right) => right.localeCompare(left));

  const latestWindow: PreviewPredictionWindow = {
    targetShowDate: config.latestTargetDate,
    referenceDate: config.latestTargetDate,
    predictedAt: config.latestPredictedAt,
    modelVersions: config.latestModelVersions,
    rowsByModel: config.latestRowsByModel,
  };

  const latestSnapshots: Partial<Record<ModelSlug, PredictionSnapshot>> = {};
  for (const model of ACTIVE_MODELS) {
    latestSnapshots[model] = makePredictionSnapshot(band, model, latestWindow);
  }

  const snapshotsByDate: Record<string, Partial<Record<ModelSlug, PredictionSnapshot>>> = {};
  for (const window of historicalWindows) {
    const snapshotsForDate: Partial<Record<ModelSlug, PredictionSnapshot>> = {};
    for (const model of ACTIVE_MODELS) {
      snapshotsForDate[model] = makePredictionSnapshot(band, model, window);
    }
    snapshotsByDate[window.referenceDate] = snapshotsForDate;
    showDetailsByDate[window.show.showDate] = makeShowDetails(window.show);
    setlistsByDate[window.show.showDate] = makeSetlistSnapshot(
      showDetailsByDate[window.show.showDate],
      config.replaySongs,
    );
  }

  return {
    band,
    nextShow,
    latestShowDate: config.latestTargetDate,
    lastShowDate: config.lastShow.showDate,
    predictionDates,
    latestSnapshots,
    snapshotsByDate,
    accuracyByModel: config.accuracyRowsByModel,
    showDetailsByDate,
    setlistsByDate,
    replayAvailableShows: [
      { showDate: config.lastShow.showDate, venueName: config.lastShow.venueName },
      { showDate: config.replayShow.showDate, venueName: config.replayShow.venueName },
    ],
    replaySelectedDate: config.lastShow.showDate,
  };
}

const PREVIEW_BANDS: Record<PreviewBandSlug, PreviewBandConfig> = {
  goose: makeBandPreview({
    slug: "goose",
    displayName: "Goose",
    nextShow: {
      showDate: "2026-05-14",
      venueName: "Mohegan Sun Arena",
      city: "Uncasville",
      state: "CT",
    },
    lastShow: {
      showDate: "2026-04-27",
      venueName: "The Eastern",
      city: "Atlanta",
      state: "GA",
    },
    replayShow: {
      showDate: "2026-04-24",
      venueName: "Fox Theatre",
      city: "Boulder",
      state: "CO",
    },
    latestTargetDate: "2026-05-14",
    predictionDates: ["2026-05-14", "2026-04-24", "2026-04-18"],
    latestPredictedAt: "2026-05-02T14:05:00Z",
    latestModelVersions: {
      notebook: "notebook_preview_v1",
      deal: "deal_preview_v1",
    },
    latestRowsByModel: {
      notebook: [
        row("Hungersite", 0.31, 8, 2, 18, "2026-04-20", { gapRatio: 1.4, gapZScore: 1.1 }),
        row("Arcadia", 0.28, 5, 4, 21, "2026-04-24", { gapRatio: 1.2, gapZScore: 0.9 }),
        row("Dripfield", 0.24, 3, 6, 16, "2026-04-27", { gapRatio: 1.0, gapZScore: 0.7 }),
        row("Empress of Organos", 0.21, 12, 1, 11, "2026-04-16", { gapRatio: 1.6, gapZScore: 1.3 }),
        row("Silver Rising", 0.19, 9, 3, 14, "2026-04-19"),
        row("Hot Tea", 0.17, 14, 2, 13, "2026-04-15"),
        row("Borne", 0.15, 7, 5, 12, "2026-04-23"),
        row("Creatures", 0.13, 11, 1, 10, "2026-04-12"),
        row("Red Bird", 0.11, 10, 2, 9, "2026-04-18"),
        row("Tumble", 0.09, 16, 0, 7, "2026-04-02"),
        row("Slow Ready", 0.07, 18, 0, 6, "2026-03-28"),
        row("So Ready", 0.05, 22, 0, 4, "2026-03-20"),
      ],
      deal: [
        row("Arcadia", 0.34, 5, 4, 21, "2026-04-24", { gapRatio: 1.1, gapZScore: 1.0 }),
        row("Hungersite", 0.3, 8, 2, 18, "2026-04-20", { gapRatio: 1.5, gapZScore: 1.2 }),
        row("Empress of Organos", 0.26, 12, 1, 11, "2026-04-16", { gapRatio: 1.7, gapZScore: 1.4 }),
        row("Dripfield", 0.23, 3, 6, 16, "2026-04-27"),
        row("Silver Rising", 0.2, 9, 3, 14, "2026-04-19"),
        row("Hot Tea", 0.18, 14, 2, 13, "2026-04-15"),
        row("Borne", 0.15, 7, 5, 12, "2026-04-23"),
        row("Creatures", 0.14, 11, 1, 10, "2026-04-12"),
        row("Red Bird", 0.1, 10, 2, 9, "2026-04-18"),
        row("Tumble", 0.08, 16, 0, 7, "2026-04-02"),
        row("Slow Ready", 0.06, 18, 0, 6, "2026-03-28"),
        row("So Ready", 0.05, 22, 0, 4, "2026-03-20"),
      ],
    },
    historicalWindows: [
      {
        show: {
          showDate: "2026-04-24",
          venueName: "Fox Theatre",
          city: "Boulder",
          state: "CO",
        },
        targetShowDate: "2026-04-24",
        referenceDate: "2026-04-24",
        predictedAt: "2026-04-24T15:10:00Z",
        modelVersions: {
          notebook: "notebook_preview_v1",
          deal: "deal_preview_v1",
        },
        rowsByModel: {
          notebook: [
            row("Hungersite", 0.33, 8, 2, 18, "2026-04-20"),
            row("Arcadia", 0.3, 5, 4, 21, "2026-04-24"),
            row("Dripfield", 0.25, 3, 6, 16, "2026-04-27"),
            row("Empress of Organos", 0.21, 12, 1, 11, "2026-04-16"),
            row("Silver Rising", 0.2, 9, 3, 14, "2026-04-19"),
            row("Hot Tea", 0.18, 14, 2, 13, "2026-04-15"),
            row("Borne", 0.16, 7, 5, 12, "2026-04-23"),
            row("Creatures", 0.14, 11, 1, 10, "2026-04-12"),
            row("Red Bird", 0.12, 10, 2, 9, "2026-04-18"),
            row("Tumble", 0.1, 16, 0, 7, "2026-04-02"),
          ],
          deal: [
            row("Arcadia", 0.35, 5, 4, 21, "2026-04-24"),
            row("Hungersite", 0.31, 8, 2, 18, "2026-04-20"),
            row("Empress of Organos", 0.26, 12, 1, 11, "2026-04-16"),
            row("Dripfield", 0.24, 3, 6, 16, "2026-04-27"),
            row("Silver Rising", 0.2, 9, 3, 14, "2026-04-19"),
            row("Hot Tea", 0.19, 14, 2, 13, "2026-04-15"),
            row("Borne", 0.16, 7, 5, 12, "2026-04-23"),
            row("Creatures", 0.14, 11, 1, 10, "2026-04-12"),
            row("Red Bird", 0.11, 10, 2, 9, "2026-04-18"),
            row("Tumble", 0.09, 16, 0, 7, "2026-04-02"),
          ],
        },
      },
      {
        show: {
          showDate: "2026-04-18",
          venueName: "Hampton Coliseum",
          city: "Hampton",
          state: "VA",
        },
        targetShowDate: "2026-04-18",
        referenceDate: "2026-04-18",
        predictedAt: "2026-04-18T15:10:00Z",
        modelVersions: {
          notebook: "notebook_preview_v1",
          deal: "deal_preview_v1",
        },
        rowsByModel: {
          notebook: [
            row("Borne", 0.3, 7, 5, 12, "2026-04-23"),
            row("Arcadia", 0.28, 5, 4, 21, "2026-04-24"),
            row("Hungersite", 0.26, 8, 2, 18, "2026-04-20"),
            row("Dripfield", 0.24, 3, 6, 16, "2026-04-27"),
            row("Empress of Organos", 0.2, 12, 1, 11, "2026-04-16"),
            row("Silver Rising", 0.18, 9, 3, 14, "2026-04-19"),
            row("Hot Tea", 0.17, 14, 2, 13, "2026-04-15"),
            row("Creatures", 0.15, 11, 1, 10, "2026-04-12"),
            row("Red Bird", 0.13, 10, 2, 9, "2026-04-18"),
            row("Tumble", 0.1, 16, 0, 7, "2026-04-02"),
          ],
          deal: [
            row("Arcadia", 0.32, 5, 4, 21, "2026-04-24"),
            row("Borne", 0.29, 7, 5, 12, "2026-04-23"),
            row("Hungersite", 0.27, 8, 2, 18, "2026-04-20"),
            row("Dripfield", 0.23, 3, 6, 16, "2026-04-27"),
            row("Empress of Organos", 0.22, 12, 1, 11, "2026-04-16"),
            row("Silver Rising", 0.19, 9, 3, 14, "2026-04-19"),
            row("Hot Tea", 0.18, 14, 2, 13, "2026-04-15"),
            row("Creatures", 0.15, 11, 1, 10, "2026-04-12"),
            row("Red Bird", 0.12, 10, 2, 9, "2026-04-18"),
            row("Tumble", 0.09, 16, 0, 7, "2026-04-02"),
          ],
        },
      },
    ],
    accuracyRowsByModel: {
      notebook: makeAccuracyRows([
        { showDate: "2026-04-24", venueName: "Fox Theatre", city: "Boulder", state: "CO", k10Recall: 0.6, k25Recall: 0.72, k50Recall: 0.85, k10Precision: 0.48, k25Precision: 0.44, k50Precision: 0.35 },
        { showDate: "2026-04-18", venueName: "Hampton Coliseum", city: "Hampton", state: "VA", k10Recall: 0.5, k25Recall: 0.68, k50Recall: 0.82, k10Precision: 0.44, k25Precision: 0.4, k50Precision: 0.32 },
        { showDate: "2026-04-11", venueName: "The Eastern", city: "Atlanta", state: "GA", k10Recall: 0.55, k25Recall: 0.7, k50Recall: 0.83, k10Precision: 0.47, k25Precision: 0.42, k50Precision: 0.33 },
        { showDate: "2026-04-04", venueName: "The Anthem", city: "Washington", state: "DC", k10Recall: 0.58, k25Recall: 0.71, k50Recall: 0.84, k10Precision: 0.46, k25Precision: 0.41, k50Precision: 0.34 },
        { showDate: "2026-03-28", venueName: "Madison Square Garden", city: "New York", state: "NY", k10Recall: 0.57, k25Recall: 0.69, k50Recall: 0.81, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.31 },
        { showDate: "2026-03-21", venueName: "Riviera Theatre", city: "Chicago", state: "IL", k10Recall: 0.52, k25Recall: 0.67, k50Recall: 0.8, k10Precision: 0.43, k25Precision: 0.39, k50Precision: 0.3 },
      ]),
      deal: makeAccuracyRows([
        { showDate: "2026-04-24", venueName: "Fox Theatre", city: "Boulder", state: "CO", k10Recall: 0.65, k25Recall: 0.75, k50Recall: 0.86, k10Precision: 0.52, k25Precision: 0.45, k50Precision: 0.36 },
        { showDate: "2026-04-18", venueName: "Hampton Coliseum", city: "Hampton", state: "VA", k10Recall: 0.54, k25Recall: 0.69, k50Recall: 0.84, k10Precision: 0.46, k25Precision: 0.41, k50Precision: 0.33 },
        { showDate: "2026-04-11", venueName: "The Eastern", city: "Atlanta", state: "GA", k10Recall: 0.59, k25Recall: 0.72, k50Recall: 0.84, k10Precision: 0.48, k25Precision: 0.42, k50Precision: 0.34 },
        { showDate: "2026-04-04", venueName: "The Anthem", city: "Washington", state: "DC", k10Recall: 0.61, k25Recall: 0.73, k50Recall: 0.85, k10Precision: 0.49, k25Precision: 0.43, k50Precision: 0.35 },
        { showDate: "2026-03-28", venueName: "Madison Square Garden", city: "New York", state: "NY", k10Recall: 0.6, k25Recall: 0.71, k50Recall: 0.83, k10Precision: 0.47, k25Precision: 0.41, k50Precision: 0.33 },
        { showDate: "2026-03-21", venueName: "Riviera Theatre", city: "Chicago", state: "IL", k10Recall: 0.56, k25Recall: 0.68, k50Recall: 0.81, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.31 },
      ]),
    },
    replaySongs: ["Hungersite", "Arcadia", "Dripfield", "Empress of Organos", "Silver Rising", "Hot Tea", "Borne", "Creatures", "Red Bird", "Tumble", "Slow Ready", "So Ready"],
  }),
  phish: makeBandPreview({
    slug: "phish",
    displayName: "Phish",
    nextShow: {
      showDate: "2026-05-02",
      venueName: "Sphere",
      city: "Las Vegas",
      state: "NV",
    },
    lastShow: {
      showDate: "2026-04-30",
      venueName: "United Center",
      city: "Chicago",
      state: "IL",
    },
    replayShow: {
      showDate: "2026-04-23",
      venueName: "Madison Square Garden",
      city: "New York",
      state: "NY",
    },
    latestTargetDate: "2026-05-02",
    predictionDates: ["2026-05-02", "2026-04-23", "2026-04-16"],
    latestPredictedAt: "2026-05-02T14:15:00Z",
    latestModelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
    latestRowsByModel: {
      notebook: [
        row("Tweezer", 0.33, 4, 5, 22, "2026-04-30"),
        row("Ghost", 0.29, 6, 4, 20, "2026-04-28"),
        row("Stash", 0.26, 8, 3, 19, "2026-04-27"),
        row("Reba", 0.22, 11, 2, 17, "2026-04-26"),
        row("Fuego", 0.2, 13, 2, 15, "2026-04-24"),
        row("Chalk Dust Torture", 0.18, 7, 6, 16, "2026-04-29"),
        row("Down with Disease", 0.17, 10, 3, 14, "2026-04-25"),
        row("Bathtub Gin", 0.15, 9, 3, 13, "2026-04-21"),
        row("Harry Hood", 0.14, 12, 2, 12, "2026-04-19"),
        row("Carini", 0.12, 15, 1, 10, "2026-04-15"),
        row("Waste", 0.1, 17, 1, 9, "2026-04-10"),
        row("Theme From the Bottom", 0.08, 18, 0, 8, "2026-04-06"),
      ],
      deal: [
        row("Ghost", 0.34, 6, 4, 20, "2026-04-28"),
        row("Tweezer", 0.31, 4, 5, 22, "2026-04-30"),
        row("Chalk Dust Torture", 0.27, 7, 6, 16, "2026-04-29"),
        row("Stash", 0.24, 8, 3, 19, "2026-04-27"),
        row("Reba", 0.21, 11, 2, 17, "2026-04-26"),
        row("Fuego", 0.19, 13, 2, 15, "2026-04-24"),
        row("Down with Disease", 0.18, 10, 3, 14, "2026-04-25"),
        row("Bathtub Gin", 0.16, 9, 3, 13, "2026-04-21"),
        row("Harry Hood", 0.15, 12, 2, 12, "2026-04-19"),
        row("Carini", 0.13, 15, 1, 10, "2026-04-15"),
        row("Waste", 0.11, 17, 1, 9, "2026-04-10"),
        row("Theme From the Bottom", 0.09, 18, 0, 8, "2026-04-06"),
      ],
    },
    historicalWindows: [
      {
        show: {
          showDate: "2026-04-23",
          venueName: "Madison Square Garden",
          city: "New York",
          state: "NY",
        },
        targetShowDate: "2026-04-23",
        referenceDate: "2026-04-23",
        predictedAt: "2026-04-23T15:10:00Z",
        modelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
        rowsByModel: {
          notebook: [
            row("Tweezer", 0.34, 4, 5, 22, "2026-04-30"),
            row("Ghost", 0.3, 6, 4, 20, "2026-04-28"),
            row("Stash", 0.27, 8, 3, 19, "2026-04-27"),
            row("Reba", 0.23, 11, 2, 17, "2026-04-26"),
            row("Fuego", 0.21, 13, 2, 15, "2026-04-24"),
            row("Chalk Dust Torture", 0.19, 7, 6, 16, "2026-04-29"),
            row("Down with Disease", 0.18, 10, 3, 14, "2026-04-25"),
            row("Bathtub Gin", 0.16, 9, 3, 13, "2026-04-21"),
            row("Harry Hood", 0.15, 12, 2, 12, "2026-04-19"),
            row("Carini", 0.13, 15, 1, 10, "2026-04-15"),
          ],
          deal: [
            row("Ghost", 0.35, 6, 4, 20, "2026-04-28"),
            row("Tweezer", 0.32, 4, 5, 22, "2026-04-30"),
            row("Chalk Dust Torture", 0.28, 7, 6, 16, "2026-04-29"),
            row("Stash", 0.25, 8, 3, 19, "2026-04-27"),
            row("Reba", 0.22, 11, 2, 17, "2026-04-26"),
            row("Fuego", 0.2, 13, 2, 15, "2026-04-24"),
            row("Down with Disease", 0.19, 10, 3, 14, "2026-04-25"),
            row("Bathtub Gin", 0.17, 9, 3, 13, "2026-04-21"),
            row("Harry Hood", 0.16, 12, 2, 12, "2026-04-19"),
            row("Carini", 0.14, 15, 1, 10, "2026-04-15"),
          ],
        },
      },
      {
        show: {
          showDate: "2026-04-16",
          venueName: "TD Garden",
          city: "Boston",
          state: "MA",
        },
        targetShowDate: "2026-04-16",
        referenceDate: "2026-04-16",
        predictedAt: "2026-04-16T15:10:00Z",
        modelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
        rowsByModel: {
          notebook: [
            row("Ghost", 0.32, 6, 4, 20, "2026-04-28"),
            row("Tweezer", 0.3, 4, 5, 22, "2026-04-30"),
            row("Stash", 0.26, 8, 3, 19, "2026-04-27"),
            row("Reba", 0.24, 11, 2, 17, "2026-04-26"),
            row("Fuego", 0.2, 13, 2, 15, "2026-04-24"),
            row("Chalk Dust Torture", 0.18, 7, 6, 16, "2026-04-29"),
            row("Down with Disease", 0.17, 10, 3, 14, "2026-04-25"),
            row("Bathtub Gin", 0.16, 9, 3, 13, "2026-04-21"),
            row("Harry Hood", 0.14, 12, 2, 12, "2026-04-19"),
            row("Carini", 0.12, 15, 1, 10, "2026-04-15"),
          ],
          deal: [
            row("Tweezer", 0.33, 4, 5, 22, "2026-04-30"),
            row("Ghost", 0.31, 6, 4, 20, "2026-04-28"),
            row("Chalk Dust Torture", 0.27, 7, 6, 16, "2026-04-29"),
            row("Stash", 0.25, 8, 3, 19, "2026-04-27"),
            row("Reba", 0.22, 11, 2, 17, "2026-04-26"),
            row("Fuego", 0.2, 13, 2, 15, "2026-04-24"),
            row("Down with Disease", 0.18, 10, 3, 14, "2026-04-25"),
            row("Bathtub Gin", 0.17, 9, 3, 13, "2026-04-21"),
            row("Harry Hood", 0.15, 12, 2, 12, "2026-04-19"),
            row("Carini", 0.13, 15, 1, 10, "2026-04-15"),
          ],
        },
      },
    ],
    accuracyRowsByModel: {
      notebook: makeAccuracyRows([
        { showDate: "2026-04-23", venueName: "Madison Square Garden", city: "New York", state: "NY", k10Recall: 0.58, k25Recall: 0.7, k50Recall: 0.82, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.32 },
        { showDate: "2026-04-16", venueName: "TD Garden", city: "Boston", state: "MA", k10Recall: 0.56, k25Recall: 0.68, k50Recall: 0.81, k10Precision: 0.44, k25Precision: 0.39, k50Precision: 0.31 },
        { showDate: "2026-04-09", venueName: "MGM Grand Garden Arena", city: "Las Vegas", state: "NV", k10Recall: 0.59, k25Recall: 0.71, k50Recall: 0.83, k10Precision: 0.46, k25Precision: 0.41, k50Precision: 0.33 },
        { showDate: "2026-04-02", venueName: "Climate Pledge Arena", city: "Seattle", state: "WA", k10Recall: 0.57, k25Recall: 0.69, k50Recall: 0.81, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.32 },
        { showDate: "2026-03-26", venueName: "United Center", city: "Chicago", state: "IL", k10Recall: 0.55, k25Recall: 0.67, k50Recall: 0.8, k10Precision: 0.43, k25Precision: 0.38, k50Precision: 0.3 },
        { showDate: "2026-03-19", venueName: "The Forum", city: "Inglewood", state: "CA", k10Recall: 0.54, k25Recall: 0.66, k50Recall: 0.79, k10Precision: 0.42, k25Precision: 0.37, k50Precision: 0.29 },
      ]),
      deal: makeAccuracyRows([
        { showDate: "2026-04-23", venueName: "Madison Square Garden", city: "New York", state: "NY", k10Recall: 0.6, k25Recall: 0.72, k50Recall: 0.84, k10Precision: 0.47, k25Precision: 0.41, k50Precision: 0.33 },
        { showDate: "2026-04-16", venueName: "TD Garden", city: "Boston", state: "MA", k10Recall: 0.58, k25Recall: 0.7, k50Recall: 0.82, k10Precision: 0.46, k25Precision: 0.4, k50Precision: 0.32 },
        { showDate: "2026-04-09", venueName: "MGM Grand Garden Arena", city: "Las Vegas", state: "NV", k10Recall: 0.61, k25Recall: 0.73, k50Recall: 0.84, k10Precision: 0.48, k25Precision: 0.42, k50Precision: 0.34 },
        { showDate: "2026-04-02", venueName: "Climate Pledge Arena", city: "Seattle", state: "WA", k10Recall: 0.59, k25Recall: 0.71, k50Recall: 0.82, k10Precision: 0.46, k25Precision: 0.41, k50Precision: 0.33 },
        { showDate: "2026-03-26", venueName: "United Center", city: "Chicago", state: "IL", k10Recall: 0.57, k25Recall: 0.69, k50Recall: 0.81, k10Precision: 0.44, k25Precision: 0.39, k50Precision: 0.31 },
        { showDate: "2026-03-19", venueName: "The Forum", city: "Inglewood", state: "CA", k10Recall: 0.55, k25Recall: 0.67, k50Recall: 0.8, k10Precision: 0.43, k25Precision: 0.38, k50Precision: 0.3 },
      ]),
    },
    replaySongs: ["Tweezer", "Ghost", "Stash", "Reba", "Fuego", "Chalk Dust Torture", "Down with Disease", "Bathtub Gin", "Harry Hood", "Carini", "Waste", "Theme From the Bottom"],
  }),
  wsp: makeBandPreview({
    slug: "wsp",
    displayName: "Widespread Panic",
    nextShow: {
      showDate: "2026-05-09",
      venueName: "Red Rocks Amphitheatre",
      city: "Morrison",
      state: "CO",
    },
    lastShow: {
      showDate: "2026-04-25",
      venueName: "Mann Center",
      city: "Philadelphia",
      state: "PA",
    },
    replayShow: {
      showDate: "2026-04-19",
      venueName: "The Fillmore",
      city: "New Orleans",
      state: "LA",
    },
    latestTargetDate: "2026-05-09",
    predictionDates: ["2026-05-09", "2026-04-19", "2026-04-12"],
    latestPredictedAt: "2026-05-02T14:25:00Z",
    latestModelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
    latestRowsByModel: {
      notebook: [
        row("A of D", 0.32, 4, 5, 18, "2026-04-25"),
        row("Jack", 0.3, 6, 4, 17, "2026-04-24"),
        row("Travelin' Light", 0.27, 8, 3, 16, "2026-04-22"),
        row("Pigeons", 0.24, 10, 2, 15, "2026-04-21"),
        row("Pickin' Up the Pieces", 0.21, 11, 2, 14, "2026-04-20"),
        row("Fishwater", 0.19, 13, 1, 13, "2026-04-18"),
        row("Conrad", 0.18, 9, 3, 12, "2026-04-23"),
        row("Blackout Blues", 0.16, 14, 1, 11, "2026-04-17"),
        row("C. Brown", 0.15, 12, 2, 10, "2026-04-15"),
        row("The Take Out", 0.13, 15, 1, 9, "2026-04-10"),
        row("North", 0.1, 18, 0, 8, "2026-04-03"),
        row("Little Kin", 0.08, 20, 0, 7, "2026-03-30"),
      ],
      deal: [
        row("Jack", 0.34, 6, 4, 17, "2026-04-24"),
        row("A of D", 0.31, 4, 5, 18, "2026-04-25"),
        row("Travelin' Light", 0.28, 8, 3, 16, "2026-04-22"),
        row("Pigeons", 0.25, 10, 2, 15, "2026-04-21"),
        row("Conrad", 0.23, 9, 3, 12, "2026-04-23"),
        row("Pickin' Up the Pieces", 0.2, 11, 2, 14, "2026-04-20"),
        row("Fishwater", 0.18, 13, 1, 13, "2026-04-18"),
        row("Blackout Blues", 0.17, 14, 1, 11, "2026-04-17"),
        row("C. Brown", 0.15, 12, 2, 10, "2026-04-15"),
        row("The Take Out", 0.13, 15, 1, 9, "2026-04-10"),
        row("North", 0.1, 18, 0, 8, "2026-04-03"),
        row("Little Kin", 0.08, 20, 0, 7, "2026-03-30"),
      ],
    },
    historicalWindows: [
      {
        show: {
          showDate: "2026-04-19",
          venueName: "The Fillmore",
          city: "New Orleans",
          state: "LA",
        },
        targetShowDate: "2026-04-19",
        referenceDate: "2026-04-19",
        predictedAt: "2026-04-19T15:10:00Z",
        modelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
        rowsByModel: {
          notebook: [
            row("A of D", 0.33, 4, 5, 18, "2026-04-25"),
            row("Jack", 0.3, 6, 4, 17, "2026-04-24"),
            row("Travelin' Light", 0.28, 8, 3, 16, "2026-04-22"),
            row("Pigeons", 0.24, 10, 2, 15, "2026-04-21"),
            row("Pickin' Up the Pieces", 0.22, 11, 2, 14, "2026-04-20"),
            row("Fishwater", 0.2, 13, 1, 13, "2026-04-18"),
            row("Conrad", 0.18, 9, 3, 12, "2026-04-23"),
            row("Blackout Blues", 0.16, 14, 1, 11, "2026-04-17"),
            row("C. Brown", 0.15, 12, 2, 10, "2026-04-15"),
            row("The Take Out", 0.13, 15, 1, 9, "2026-04-10"),
          ],
          deal: [
            row("Jack", 0.34, 6, 4, 17, "2026-04-24"),
            row("A of D", 0.31, 4, 5, 18, "2026-04-25"),
            row("Travelin' Light", 0.29, 8, 3, 16, "2026-04-22"),
            row("Pigeons", 0.25, 10, 2, 15, "2026-04-21"),
            row("Conrad", 0.23, 9, 3, 12, "2026-04-23"),
            row("Pickin' Up the Pieces", 0.21, 11, 2, 14, "2026-04-20"),
            row("Fishwater", 0.19, 13, 1, 13, "2026-04-18"),
            row("Blackout Blues", 0.17, 14, 1, 11, "2026-04-17"),
            row("C. Brown", 0.15, 12, 2, 10, "2026-04-15"),
            row("The Take Out", 0.13, 15, 1, 9, "2026-04-10"),
          ],
        },
      },
      {
        show: {
          showDate: "2026-04-12",
          venueName: "St. Augustine Amphitheatre",
          city: "St. Augustine",
          state: "FL",
        },
        targetShowDate: "2026-04-12",
        referenceDate: "2026-04-12",
        predictedAt: "2026-04-12T15:10:00Z",
        modelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
        rowsByModel: {
          notebook: [
            row("Jack", 0.31, 6, 4, 17, "2026-04-24"),
            row("A of D", 0.29, 4, 5, 18, "2026-04-25"),
            row("Travelin' Light", 0.27, 8, 3, 16, "2026-04-22"),
            row("Pigeons", 0.25, 10, 2, 15, "2026-04-21"),
            row("Conrad", 0.23, 9, 3, 12, "2026-04-23"),
            row("Pickin' Up the Pieces", 0.21, 11, 2, 14, "2026-04-20"),
            row("Fishwater", 0.2, 13, 1, 13, "2026-04-18"),
            row("Blackout Blues", 0.17, 14, 1, 11, "2026-04-17"),
            row("C. Brown", 0.15, 12, 2, 10, "2026-04-15"),
            row("The Take Out", 0.13, 15, 1, 9, "2026-04-10"),
          ],
          deal: [
            row("A of D", 0.32, 4, 5, 18, "2026-04-25"),
            row("Jack", 0.3, 6, 4, 17, "2026-04-24"),
            row("Travelin' Light", 0.28, 8, 3, 16, "2026-04-22"),
            row("Pigeons", 0.26, 10, 2, 15, "2026-04-21"),
            row("Conrad", 0.24, 9, 3, 12, "2026-04-23"),
            row("Pickin' Up the Pieces", 0.22, 11, 2, 14, "2026-04-20"),
            row("Fishwater", 0.2, 13, 1, 13, "2026-04-18"),
            row("Blackout Blues", 0.17, 14, 1, 11, "2026-04-17"),
            row("C. Brown", 0.15, 12, 2, 10, "2026-04-15"),
            row("The Take Out", 0.13, 15, 1, 9, "2026-04-10"),
          ],
        },
      },
    ],
    accuracyRowsByModel: {
      notebook: makeAccuracyRows([
        { showDate: "2026-04-19", venueName: "The Fillmore", city: "New Orleans", state: "LA", k10Recall: 0.57, k25Recall: 0.69, k50Recall: 0.81, k10Precision: 0.44, k25Precision: 0.39, k50Precision: 0.31 },
        { showDate: "2026-04-12", venueName: "St. Augustine Amphitheatre", city: "St. Augustine", state: "FL", k10Recall: 0.55, k25Recall: 0.68, k50Recall: 0.8, k10Precision: 0.43, k25Precision: 0.38, k50Precision: 0.3 },
        { showDate: "2026-04-05", venueName: "The Wharf Amphitheater", city: "Orange Beach", state: "AL", k10Recall: 0.58, k25Recall: 0.7, k50Recall: 0.82, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.32 },
        { showDate: "2026-03-29", venueName: "The Amp at Log Still", city: "Gethsemane", state: "KY", k10Recall: 0.56, k25Recall: 0.67, k50Recall: 0.8, k10Precision: 0.43, k25Precision: 0.38, k50Precision: 0.3 },
        { showDate: "2026-03-22", venueName: "Fox Theatre", city: "Atlanta", state: "GA", k10Recall: 0.54, k25Recall: 0.66, k50Recall: 0.79, k10Precision: 0.42, k25Precision: 0.37, k50Precision: 0.29 },
        { showDate: "2026-03-15", venueName: "Hard Rock Live", city: "Biloxi", state: "MS", k10Recall: 0.53, k25Recall: 0.65, k50Recall: 0.78, k10Precision: 0.41, k25Precision: 0.36, k50Precision: 0.28 },
      ]),
      deal: makeAccuracyRows([
        { showDate: "2026-04-19", venueName: "The Fillmore", city: "New Orleans", state: "LA", k10Recall: 0.61, k25Recall: 0.72, k50Recall: 0.84, k10Precision: 0.47, k25Precision: 0.41, k50Precision: 0.33 },
        { showDate: "2026-04-12", venueName: "St. Augustine Amphitheatre", city: "St. Augustine", state: "FL", k10Recall: 0.58, k25Recall: 0.7, k50Recall: 0.82, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.31 },
        { showDate: "2026-04-05", venueName: "The Wharf Amphitheater", city: "Orange Beach", state: "AL", k10Recall: 0.6, k25Recall: 0.72, k50Recall: 0.83, k10Precision: 0.46, k25Precision: 0.41, k50Precision: 0.32 },
        { showDate: "2026-03-29", venueName: "The Amp at Log Still", city: "Gethsemane", state: "KY", k10Recall: 0.57, k25Recall: 0.68, k50Recall: 0.8, k10Precision: 0.44, k25Precision: 0.39, k50Precision: 0.3 },
        { showDate: "2026-03-22", venueName: "Fox Theatre", city: "Atlanta", state: "GA", k10Recall: 0.55, k25Recall: 0.67, k50Recall: 0.79, k10Precision: 0.43, k25Precision: 0.38, k50Precision: 0.29 },
        { showDate: "2026-03-15", venueName: "Hard Rock Live", city: "Biloxi", state: "MS", k10Recall: 0.54, k25Recall: 0.66, k50Recall: 0.78, k10Precision: 0.42, k25Precision: 0.37, k50Precision: 0.28 },
      ]),
    },
    replaySongs: ["A of D", "Jack", "Travelin' Light", "Pigeons", "Pickin' Up the Pieces", "Fishwater", "Conrad", "Blackout Blues", "C. Brown", "The Take Out", "North", "Little Kin"],
  }),
  billy: makeBandPreview({
    slug: "billy",
    displayName: "Billy Strings",
    nextShow: {
      showDate: "2026-05-12",
      venueName: "Austin City Limits Live",
      city: "Austin",
      state: "TX",
    },
    lastShow: {
      showDate: "2026-04-29",
      venueName: "Mission Ballroom",
      city: "Denver",
      state: "CO",
    },
    replayShow: {
      showDate: "2026-04-21",
      venueName: "Ryman Auditorium",
      city: "Nashville",
      state: "TN",
    },
    latestTargetDate: "2026-05-12",
    predictionDates: ["2026-05-12", "2026-04-21", "2026-04-14"],
    latestPredictedAt: "2026-05-02T14:35:00Z",
    latestModelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
    latestRowsByModel: {
      notebook: [
        row("Dust in a Baggie", 0.31, 5, 4, 19, "2026-04-29"),
        row("Away From the Mire", 0.29, 6, 3, 18, "2026-04-28"),
        row("Heartbeat of America", 0.27, 8, 2, 17, "2026-04-27"),
        row("Turmoil & Tinfoil", 0.24, 10, 2, 16, "2026-04-26"),
        row("John Deere Tractor", 0.22, 12, 1, 15, "2026-04-24"),
        row("Hide and Seek", 0.2, 13, 1, 14, "2026-04-23"),
        row("Secrets", 0.18, 9, 3, 13, "2026-04-25"),
        row("Running the Route", 0.16, 11, 2, 12, "2026-04-20"),
        row("River", 0.15, 14, 1, 11, "2026-04-18"),
        row("Home", 0.13, 15, 1, 10, "2026-04-16"),
        row("Highway Hypnosis", 0.11, 17, 0, 9, "2026-04-10"),
        row("Little Maggie", 0.09, 19, 0, 8, "2026-04-04"),
      ],
      deal: [
        row("Away From the Mire", 0.33, 6, 3, 18, "2026-04-28"),
        row("Dust in a Baggie", 0.3, 5, 4, 19, "2026-04-29"),
        row("Heartbeat of America", 0.28, 8, 2, 17, "2026-04-27"),
        row("Turmoil & Tinfoil", 0.25, 10, 2, 16, "2026-04-26"),
        row("Secrets", 0.23, 9, 3, 13, "2026-04-25"),
        row("John Deere Tractor", 0.21, 12, 1, 15, "2026-04-24"),
        row("Hide and Seek", 0.19, 13, 1, 14, "2026-04-23"),
        row("Running the Route", 0.17, 11, 2, 12, "2026-04-20"),
        row("River", 0.15, 14, 1, 11, "2026-04-18"),
        row("Home", 0.13, 15, 1, 10, "2026-04-16"),
        row("Highway Hypnosis", 0.11, 17, 0, 9, "2026-04-10"),
        row("Little Maggie", 0.09, 19, 0, 8, "2026-04-04"),
      ],
    },
    historicalWindows: [
      {
        show: {
          showDate: "2026-04-21",
          venueName: "Ryman Auditorium",
          city: "Nashville",
          state: "TN",
        },
        targetShowDate: "2026-04-21",
        referenceDate: "2026-04-21",
        predictedAt: "2026-04-21T15:10:00Z",
        modelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
        rowsByModel: {
          notebook: [
            row("Dust in a Baggie", 0.33, 5, 4, 19, "2026-04-29"),
            row("Away From the Mire", 0.3, 6, 3, 18, "2026-04-28"),
            row("Heartbeat of America", 0.28, 8, 2, 17, "2026-04-27"),
            row("Turmoil & Tinfoil", 0.25, 10, 2, 16, "2026-04-26"),
            row("John Deere Tractor", 0.23, 12, 1, 15, "2026-04-24"),
            row("Hide and Seek", 0.21, 13, 1, 14, "2026-04-23"),
            row("Secrets", 0.19, 9, 3, 13, "2026-04-25"),
            row("Running the Route", 0.17, 11, 2, 12, "2026-04-20"),
            row("River", 0.15, 14, 1, 11, "2026-04-18"),
            row("Home", 0.13, 15, 1, 10, "2026-04-16"),
          ],
          deal: [
            row("Away From the Mire", 0.34, 6, 3, 18, "2026-04-28"),
            row("Dust in a Baggie", 0.31, 5, 4, 19, "2026-04-29"),
            row("Heartbeat of America", 0.29, 8, 2, 17, "2026-04-27"),
            row("Turmoil & Tinfoil", 0.26, 10, 2, 16, "2026-04-26"),
            row("Secrets", 0.24, 9, 3, 13, "2026-04-25"),
            row("John Deere Tractor", 0.22, 12, 1, 15, "2026-04-24"),
            row("Hide and Seek", 0.2, 13, 1, 14, "2026-04-23"),
            row("Running the Route", 0.18, 11, 2, 12, "2026-04-20"),
            row("River", 0.16, 14, 1, 11, "2026-04-18"),
            row("Home", 0.14, 15, 1, 10, "2026-04-16"),
          ],
        },
      },
      {
        show: {
          showDate: "2026-04-14",
          venueName: "Bonnaroo",
          city: "Manchester",
          state: "TN",
        },
        targetShowDate: "2026-04-14",
        referenceDate: "2026-04-14",
        predictedAt: "2026-04-14T15:10:00Z",
        modelVersions: { notebook: "notebook_preview_v1", deal: "deal_preview_v1" },
        rowsByModel: {
          notebook: [
            row("Away From the Mire", 0.31, 6, 3, 18, "2026-04-28"),
            row("Dust in a Baggie", 0.3, 5, 4, 19, "2026-04-29"),
            row("Heartbeat of America", 0.28, 8, 2, 17, "2026-04-27"),
            row("Turmoil & Tinfoil", 0.24, 10, 2, 16, "2026-04-26"),
            row("John Deere Tractor", 0.22, 12, 1, 15, "2026-04-24"),
            row("Hide and Seek", 0.2, 13, 1, 14, "2026-04-23"),
            row("Secrets", 0.18, 9, 3, 13, "2026-04-25"),
            row("Running the Route", 0.17, 11, 2, 12, "2026-04-20"),
            row("River", 0.15, 14, 1, 11, "2026-04-18"),
            row("Home", 0.13, 15, 1, 10, "2026-04-16"),
          ],
          deal: [
            row("Dust in a Baggie", 0.32, 5, 4, 19, "2026-04-29"),
            row("Away From the Mire", 0.3, 6, 3, 18, "2026-04-28"),
            row("Heartbeat of America", 0.28, 8, 2, 17, "2026-04-27"),
            row("Turmoil & Tinfoil", 0.25, 10, 2, 16, "2026-04-26"),
            row("Secrets", 0.23, 9, 3, 13, "2026-04-25"),
            row("John Deere Tractor", 0.21, 12, 1, 15, "2026-04-24"),
            row("Hide and Seek", 0.19, 13, 1, 14, "2026-04-23"),
            row("Running the Route", 0.18, 11, 2, 12, "2026-04-20"),
            row("River", 0.16, 14, 1, 11, "2026-04-18"),
            row("Home", 0.14, 15, 1, 10, "2026-04-16"),
          ],
        },
      },
    ],
    accuracyRowsByModel: {
      notebook: makeAccuracyRows([
        { showDate: "2026-04-21", venueName: "Ryman Auditorium", city: "Nashville", state: "TN", k10Recall: 0.59, k25Recall: 0.71, k50Recall: 0.83, k10Precision: 0.46, k25Precision: 0.41, k50Precision: 0.33 },
        { showDate: "2026-04-14", venueName: "Bonnaroo", city: "Manchester", state: "TN", k10Recall: 0.57, k25Recall: 0.69, k50Recall: 0.81, k10Precision: 0.44, k25Precision: 0.39, k50Precision: 0.31 },
        { showDate: "2026-04-07", venueName: "The Greek Theatre", city: "Berkeley", state: "CA", k10Recall: 0.58, k25Recall: 0.7, k50Recall: 0.82, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.32 },
        { showDate: "2026-03-31", venueName: "Red Rocks Amphitheatre", city: "Morrison", state: "CO", k10Recall: 0.56, k25Recall: 0.68, k50Recall: 0.8, k10Precision: 0.43, k25Precision: 0.38, k50Precision: 0.3 },
        { showDate: "2026-03-24", venueName: "The St. Augustine Amphitheatre", city: "St. Augustine", state: "FL", k10Recall: 0.54, k25Recall: 0.66, k50Recall: 0.79, k10Precision: 0.42, k25Precision: 0.37, k50Precision: 0.29 },
        { showDate: "2026-03-17", venueName: "The Fillmore", city: "San Francisco", state: "CA", k10Recall: 0.53, k25Recall: 0.65, k50Recall: 0.78, k10Precision: 0.41, k25Precision: 0.36, k50Precision: 0.28 },
      ]),
      deal: makeAccuracyRows([
        { showDate: "2026-04-21", venueName: "Ryman Auditorium", city: "Nashville", state: "TN", k10Recall: 0.62, k25Recall: 0.73, k50Recall: 0.84, k10Precision: 0.48, k25Precision: 0.42, k50Precision: 0.34 },
        { showDate: "2026-04-14", venueName: "Bonnaroo", city: "Manchester", state: "TN", k10Recall: 0.59, k25Recall: 0.71, k50Recall: 0.82, k10Precision: 0.46, k25Precision: 0.41, k50Precision: 0.32 },
        { showDate: "2026-04-07", venueName: "The Greek Theatre", city: "Berkeley", state: "CA", k10Recall: 0.6, k25Recall: 0.72, k50Recall: 0.83, k10Precision: 0.47, k25Precision: 0.42, k50Precision: 0.33 },
        { showDate: "2026-03-31", venueName: "Red Rocks Amphitheatre", city: "Morrison", state: "CO", k10Recall: 0.58, k25Recall: 0.69, k50Recall: 0.81, k10Precision: 0.45, k25Precision: 0.4, k50Precision: 0.31 },
        { showDate: "2026-03-24", venueName: "The St. Augustine Amphitheatre", city: "St. Augustine", state: "FL", k10Recall: 0.56, k25Recall: 0.67, k50Recall: 0.8, k10Precision: 0.44, k25Precision: 0.39, k50Precision: 0.3 },
        { showDate: "2026-03-17", venueName: "The Fillmore", city: "San Francisco", state: "CA", k10Recall: 0.54, k25Recall: 0.66, k50Recall: 0.79, k10Precision: 0.42, k25Precision: 0.37, k50Precision: 0.29 },
      ]),
    },
    replaySongs: ["Dust in a Baggie", "Away From the Mire", "Heartbeat of America", "Turmoil & Tinfoil", "John Deere Tractor", "Hide and Seek", "Secrets", "Running the Route", "River", "Home", "Highway Hypnosis", "Little Maggie"],
  }),
};

export function shouldUseLocalPreview(): boolean {
  return process.env.JAMBNERD_PREVIEW_MODE === "1";
}

function getPreviewBandData(bandInput: string | undefined): PreviewBandConfig | null {
  const slug = (bandInput?.trim().toLowerCase() ?? "goose") as PreviewBandSlug;
  return PREVIEW_BANDS[slug] ?? PREVIEW_BANDS.goose;
}

export function getPreviewBands(): BandEntry[] {
  return PREVIEW_BAND_SLUGS.map((slug) => PREVIEW_BANDS[slug].band);
}

export function getPreviewCurrentModelVersion(
  model: ModelSlug,
): string {
  return `${model}_preview_v1`;
}

export function getPreviewLatestPredictions(
  bandInput: string | undefined,
  modelInput: string | undefined,
): RouteState<{ band: BandSlug; model: ModelSlug; snapshot: PredictionSnapshot }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return { status: "empty" };
  }

  const model = normalizeModel(modelInput);
  const snapshot = bandData.latestSnapshots[model] ?? bandData.latestSnapshots.notebook ?? null;
  if (!snapshot) {
    return { status: "empty" };
  }

  return { status: "ready", band: bandData.band.slug, model, snapshot };
}

export function getPreviewPredictionsForDate(
  bandInput: string | undefined,
  modelInput: string | undefined,
  referenceDate: string,
): RouteState<{ band: BandSlug; model: ModelSlug; snapshot: PredictionSnapshot }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return { status: "empty" };
  }

  const model = normalizeModel(modelInput);
  const snapshot =
    bandData.snapshotsByDate[referenceDate]?.[model] ??
    bandData.snapshotsByDate[referenceDate]?.notebook ??
    null;
  if (!snapshot) {
    return { status: "empty" };
  }

  return { status: "ready", band: bandData.band.slug, model, snapshot };
}

export function getPreviewPredictionDates(
  bandInput: string | undefined,
  modelInput: string | undefined,
): RouteState<{ band: BandSlug; model: ModelSlug; dates: string[] }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return { status: "empty" };
  }

  const model = normalizeModel(modelInput);
  return { status: "ready", band: bandData.band.slug, model, dates: bandData.predictionDates };
}

export function getPreviewRecentAccuracy(
  bandInput: string | undefined,
  modelInput: string | undefined,
  limit = 25,
): RouteState<{ band: BandSlug; model: ModelSlug; rows: AccuracyRow[] }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return { status: "empty" };
  }

  const model = normalizeModel(modelInput);
  const rows = (bandData.accuracyByModel[model] ?? bandData.accuracyByModel.notebook ?? []).slice(0, limit);
  if (rows.length === 0) {
    return { status: "empty" };
  }

  return { status: "ready", band: bandData.band.slug, model, rows };
}

export function getPreviewShowDetailsByDate(
  bandInput: string | undefined,
  showDate: string | null,
): RouteState<{ band: BandSlug; show: ShowDetails }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData || !showDate) {
    return { status: "empty" };
  }

  const show = bandData.showDetailsByDate[showDate] ?? null;
  if (!show) {
    return { status: "empty" };
  }

  return { status: "ready", band: bandData.band.slug, show };
}

export function getPreviewSetlistForDate(
  bandInput: string | undefined,
  showDate: string,
): SetlistSnapshot | null {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return null;
  }

  return bandData.setlistsByDate[showDate] ?? null;
}

export function getPreviewNextShowDetails(
  bandInput: string | undefined,
): RouteState<{ band: BandSlug; show: ShowDetails }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return { status: "empty" };
  }

  return { status: "ready", band: bandData.band.slug, show: bandData.nextShow };
}

export function getPreviewLastShowSetlist(
  bandInput: string | undefined,
): RouteState<{ band: BandSlug; setlist: SetlistSnapshot }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return { status: "empty" };
  }

  const setlist = bandData.setlistsByDate[bandData.lastShowDate] ?? null;
  if (!setlist) {
    return { status: "empty" };
  }

  return { status: "ready", band: bandData.band.slug, setlist };
}

export function getPreviewReplaySnapshot(
  bandInput: string | undefined,
  selectedDateInput?: string,
  modelAInput?: string,
  modelBInput?: string,
  replayWindow = 50,
): RouteState<{ band: BandSlug; replay: ReplaySnapshot }> {
  const bandData = getPreviewBandData(bandInput);
  if (!bandData) {
    return { status: "empty" };
  }

  const [modelA, modelB] = resolvePreviewReplayModels(modelAInput, modelBInput);
  const availableShows = bandData.replayAvailableShows.slice(0, replayWindow);
  const selectedDate =
    selectedDateInput && availableShows.some((show) => show.showDate === selectedDateInput)
      ? selectedDateInput
      : bandData.replaySelectedDate;

  const show = bandData.showDetailsByDate[selectedDate] ?? null;
  const setlist = bandData.setlistsByDate[selectedDate] ?? null;
  const snapshotsByDate = bandData.snapshotsByDate[selectedDate] ?? {};

  return {
    status: "ready",
    band: bandData.band.slug,
    replay: {
      availableShows,
      selectedDate,
      show,
      setlist,
      modelA,
      modelB,
      snapshots: {
        [modelA]: snapshotsByDate[modelA] ?? null,
        [modelB]: snapshotsByDate[modelB] ?? null,
      },
    },
  };
}

export async function getPreviewExplorerSnapshot(
  bandInput: string | undefined,
  modelInput: string | undefined,
  selectedDateInput?: string,
): Promise<RouteState<{ band: BandSlug; model: ModelSlug; explorer: ExplorerSnapshot }>> {
  const datesState = getPreviewPredictionDates(bandInput, modelInput);
  if (datesState.status !== "ready") {
    return datesState as RouteState<{ band: BandSlug; model: ModelSlug; explorer: ExplorerSnapshot }>;
  }

  const selectedDate =
    selectedDateInput && datesState.dates.includes(selectedDateInput)
      ? selectedDateInput
      : datesState.dates[0] ?? null;

  if (!selectedDate) {
    return { status: "empty" };
  }

  const predictionsState = getPreviewPredictionsForDate(datesState.band, datesState.model, selectedDate);
  const setlist = getPreviewSetlistForDate(datesState.band, selectedDate);

  if (predictionsState.status !== "ready") {
    return predictionsState as RouteState<{ band: BandSlug; model: ModelSlug; explorer: ExplorerSnapshot }>;
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
