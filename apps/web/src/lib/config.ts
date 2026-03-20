export const BAND_CONFIG = {
  eggy: {
    displayName: "Eggy",
    showsTable: "eggy_shows_raw",
  },
  billy: {
    displayName: "Billy Strings",
    showsTable: "billy_shows_raw",
  },
  goose: {
    displayName: "Goose",
    showsTable: "goose_shows_raw",
  },
  phish: {
    displayName: "Phish",
    showsTable: "phish_shows_raw",
  },
  wsp: {
    displayName: "Widespread Panic",
    showsTable: "wsp_shows_raw",
  },
  um: {
    displayName: "Umphrey's McGee",
    showsTable: "um_shows_raw",
  },
} as const;

export const MODEL_CONFIG = {
  notebook: {
    displayName: "Notebook",
    explanation:
      "Frequency-based model focused on songs active in the recent rotation while excluding the last three shows.",
  },
  ckplus: {
    displayName: "CK+",
    explanation:
      "Gap-based model that ranks songs by how overdue they are relative to their historical cadence.",
  },
} as const;

export const BAND_ID_COLUMNS: Record<BandSlug, string> = {
  eggy: "show_id",
  billy: "show_id",
  goose: "show_id",
  phish: "showid",
  wsp: "show_id",
  um: "show_id",
};

export const ACTIVE_BANDS = Object.keys(BAND_CONFIG) as BandSlug[];
export const ACTIVE_MODELS = Object.keys(MODEL_CONFIG) as ModelSlug[];

export type BandSlug = keyof typeof BAND_CONFIG;
export type ModelSlug = keyof typeof MODEL_CONFIG;

export type LikelihoodTier = "expected" | "hot" | "likely" | "possible";

export const TIER_CONFIG: Record<
  LikelihoodTier,
  { label: string; description: string; className: string; badgeClassName: string }
> = {
  expected: {
    label: "Expected",
    description: "Strongest rotation signal — high recent activity and model confidence",
    className: "text-tier-expected",
    badgeClassName: "border-tier-expected/30 bg-tier-expected-bg text-tier-expected",
  },
  hot: {
    label: "Hot",
    description: "Solid candidate — one or both models rank this song highly",
    className: "text-tier-hot",
    badgeClassName: "border-tier-hot/30 bg-tier-hot-bg text-tier-hot",
  },
  likely: {
    label: "Likely",
    description: "In the pool with a moderate signal",
    className: "text-on-surface-variant",
    badgeClassName: "border-outline-variant/30 bg-surface-container text-on-surface-variant",
  },
  possible: {
    label: "Possible",
    description: "Lower recent activity — could still appear",
    className: "text-tier-possible",
    badgeClassName: "border-tier-possible/30 bg-tier-possible-bg text-tier-possible",
  },
};

export const TIER_ORDER: LikelihoodTier[] = ["expected", "hot", "likely", "possible"];

export function normalizeBand(value?: string): BandSlug {
  return ACTIVE_BANDS.includes(value as BandSlug) ? (value as BandSlug) : "goose";
}

export function normalizeModel(value?: string): ModelSlug {
  return ACTIVE_MODELS.includes(value as ModelSlug)
    ? (value as ModelSlug)
    : "notebook";
}
