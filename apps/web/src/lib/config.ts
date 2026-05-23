export const DEFAULT_BAND_SLUG = "goose";

export type BandSlug = string;

export type LikelihoodTier = "prime" | "likely" | "possible";

export const TIER_CONFIG: Record<
  LikelihoodTier,
  { label: string; description: string; className: string; badgeClassName: string }
> = {
  prime: {
    label: "Prime",
    description: "Top 10 ranked songs by model signal",
    className: "text-tier-prime",
    badgeClassName: "border-tier-prime/30 bg-tier-prime-bg text-tier-prime",
  },
  likely: {
    label: "Likely",
    description: "Ranks 11-25 by model signal",
    className: "text-tier-likely",
    badgeClassName: "border-tier-likely/30 bg-tier-likely-bg text-tier-likely",
  },
  possible: {
    label: "Possible",
    description: "Ranks 26-50 by model signal",
    className: "text-tier-possible",
    badgeClassName: "border-tier-possible/30 bg-tier-possible-bg text-tier-possible",
  },
};

export const TIER_ORDER: LikelihoodTier[] = ["prime", "likely", "possible"];

export function normalizeBand(value?: string): BandSlug {
  const normalized = value?.trim().toLowerCase();
  return normalized && normalized.length > 0 ? normalized : DEFAULT_BAND_SLUG;
}
