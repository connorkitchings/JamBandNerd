"use client";

import { useState } from "react";

import type { PredictionRow } from "@/lib/data";
import { formatGapLabel, formatProbabilityLabel } from "@/lib/song-board";

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      aria-hidden="true"
      className={`size-4 transition-transform ${open ? "rotate-180" : ""}`}
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M6 9L12 15L18 9"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-3.5 text-green-400"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M5 12L10 17L19 7"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

function ModelAgreeIcon() {
  return (
    <svg
      aria-label="Both models predict this song"
      className="size-3.5 text-tertiary"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M9 12L11 14L15 10M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  );
}

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
