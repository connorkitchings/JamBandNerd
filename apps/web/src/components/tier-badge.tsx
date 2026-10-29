import { TIER_CONFIG, type LikelihoodTier } from "@/lib/config";

type Props = {
  tier: LikelihoodTier;
  className?: string;
};

// Text, border and fill are paired per tier so each badge stays readable in both themes.
const TIER_BADGE_CLASS: Record<LikelihoodTier, string> = {
  prime: "border-accent bg-amber-bg text-accent-text",
  likely: "border-line bg-surface-2 text-on-surface-variant",
  possible: "border-teal bg-teal-bg text-teal",
};

export function TierBadge({ tier, className }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-[0.06em] ${TIER_BADGE_CLASS[tier]} ${className ?? ""}`}
    >
      <span aria-hidden="true" className="inline-block size-1.5 rounded-full bg-current" />
      {TIER_CONFIG[tier].label}
    </span>
  );
}
