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

export const ACTIVE_MODELS = Object.keys(MODEL_CONFIG) as ModelSlug[];

export const DEFAULT_BAND_SLUG = "goose";

export type BandSlug = string;
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
  const normalized = value?.trim().toLowerCase();
  return normalized && normalized.length > 0 ? normalized : DEFAULT_BAND_SLUG;
}

export function normalizeModel(value?: string): ModelSlug {
  return ACTIVE_MODELS.includes(value as ModelSlug)
    ? (value as ModelSlug)
    : "notebook";
}
