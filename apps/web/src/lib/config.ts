export const DEFAULT_BAND_SLUG = "wsp";

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

/** Cache tag shared by every cached fetcher for a band and the revalidate route. */
export function bandCacheTag(slug: BandSlug): string {
  return `band:${slug}`;
}

/** Cache tag for the active-band list. */
export const BANDS_CACHE_TAG = "bands";

export function normalizeBand(value?: string): BandSlug {
  const normalized = value?.trim().toLowerCase();
  return normalized && normalized.length > 0 ? normalized : DEFAULT_BAND_SLUG;
}

/**
 * Show IDs and dates excluded from prediction/backtest windows (mirrors
 * `src/jambandnerd/config/bands.py`).
 */
export const EXCLUDED_PREDICTION_SHOW_IDS: Record<string, readonly string[]> = {
  goose: [
    "1755099318", // 2025-08-13 TV appearance
    "1748090458", // 2025-05-25 Napa short set (4 songs; full show same day)
    "1745685585", // 2025-04-25 short set (3 songs)
    "1741108426", // 2025-03-11 promo (1 song)
    "1730168333", // 2024-11-24 MSG short set (5 songs)
  ],
  eggy: [],
  phish: [
    "1785867540", // 2026-10-10 Huntsville show postponed to 2026-10-12
  ],
  wsp: [],
  billy: [],
  um: [],
};

export const EXCLUDED_PREDICTION_SHOW_DATES: Record<string, readonly string[]> = {
  goose: [],
  eggy: [],
  phish: [],
  wsp: [],
  billy: [],
  um: [],
};
