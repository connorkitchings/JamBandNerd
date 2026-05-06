"use client";

import { useState } from "react";

import type { PredictionRow } from "@/lib/data";
import { formatGapLabel, formatProbabilityLabel } from "@/lib/song-board";
import { CheckIcon, ChevronIcon, ModelAgreeIcon } from "@/components/icons";

export function DealMobileRow({
  row,
  isHighlighted,
  agreesWithOtherModel,
}: {
  row: PredictionRow;
  isHighlighted: boolean;
  agreesWithOtherModel: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const probabilityLabel = formatProbabilityLabel(row.probability);

  const gapLabel = formatGapLabel(row.currentGap);

  const statusBadges: React.ReactNode[] = [];
  if (isHighlighted) {
    statusBadges.push(
      <span key="played" className="inline-flex items-center gap-1 text-green-300">
        <CheckIcon /> Played
      </span>
    );
  }
  if (agreesWithOtherModel) {
    statusBadges.push(
      <span key="both" className="inline-flex items-center gap-1 text-primary">
        <ModelAgreeIcon /> Both
      </span>
    );
  }

  return (
    <div
      data-testid="deal-mobile-song-row"
      className={`px-4 py-3 ${isHighlighted ? "bg-green-950/20" : ""}`}
    >
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full min-w-0 items-center gap-3 text-left"
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-container-high/60 font-headline text-sm font-bold tabular-nums text-on-surface-variant">
          {row.rank}
        </span>
        <p
          className={`min-w-0 flex-1 break-words font-headline text-base leading-5 font-semibold ${isHighlighted ? "text-green-300" : "text-on-surface"}`}
        >
          {row.songName}
        </p>
        <span className="shrink-0 font-mono text-sm font-semibold tabular-nums text-primary">
          {probabilityLabel}
        </span>
        <span className="shrink-0 text-on-surface-variant">
          <ChevronIcon open={isOpen} />
        </span>
      </button>

      {isOpen && (
        <div className="mt-2 pl-11 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div className="text-on-surface-variant">
            Gap: <span className="font-mono tabular-nums text-on-surface">{gapLabel}</span>
          </div>
          {row.recentPlays50 !== null && (
            <div className="text-on-surface-variant">
              Recent:{" "}
              <span className="font-mono tabular-nums text-on-surface">
                {row.recentPlays50}/50
              </span>
            </div>
          )}
          {statusBadges.length > 0 && (
            <div className="col-span-2 inline-flex items-center gap-2 pt-0.5">
              {statusBadges}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
