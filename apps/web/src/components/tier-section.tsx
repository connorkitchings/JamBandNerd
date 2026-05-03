"use client";

import { useState } from "react";

import type { PredictionRow } from "@/lib/data";
import type { LikelihoodTier } from "@/lib/config";
import { TierDesktopTable } from "@/components/song-board";
import { TierMobileList } from "@/components/song-board";
import { TierSectionHeader } from "@/components/song-board";

type TierSectionProps = {
  tier: LikelihoodTier;
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  secondarySongs?: Set<string>;
  defaultOpen: boolean;
  compact?: boolean;
  modelSlug?: string;
};

export function TierSection({
  tier,
  rows,
  highlightSongs,
  secondarySongs,
  defaultOpen,
  compact,
  modelSlug,
}: TierSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (rows.length === 0) return null;

  return (
    <div className="editorial-panel overflow-hidden rounded-[1.5rem]">
      <TierSectionHeader
        tier={tier}
        rowCount={rows.length}
        isOpen={isOpen}
        onExpand={() => setIsOpen(true)}
      />

      <div
        id={`tier-content-${tier}`}
        className="w-full border-t border-outline-variant/15 bg-surface-container-low/65"
        hidden={!isOpen}
      >
        <TierDesktopTable
          compact={compact}
          highlightSongs={highlightSongs}
          rows={rows}
          modelSlug={modelSlug}
        />
        <TierMobileList
          rows={rows}
          highlightSongs={highlightSongs}
          secondarySongs={secondarySongs}
          modelSlug={modelSlug}
        />

        <div className="border-t border-outline-variant/10 px-4 py-3">
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="w-full rounded-full border border-outline-variant/20 bg-surface/75 px-4 py-2 text-center font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
          >
            Collapse
          </button>
        </div>
      </div>
    </div>
  );
}
