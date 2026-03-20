import { TIER_CONFIG, type LikelihoodTier } from "@/lib/config";

type Props = {
  tier: LikelihoodTier;
  className?: string;
};

export function TierBadge({ tier, className }: Props) {
  const config = TIER_CONFIG[tier];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-label text-[10px] font-medium uppercase tracking-[0.14rem] ${config.badgeClassName} ${className ?? ""}`}
    >
      <span className="inline-block size-1.5 rounded-full bg-current" />
      {config.label}
    </span>
  );
}
