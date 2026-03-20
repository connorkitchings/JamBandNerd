"use client";

import { useState } from "react";

import type { PredictionRow } from "@/lib/data";
import { TIER_ORDER, type LikelihoodTier } from "@/lib/config";
import { TierBadge } from "@/components/tier-badge";

type Props = {
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  compact?: boolean;
};

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

function normalizeSongName(value: string) {
  return value.trim().toLowerCase();
}

function TierSection({
  tier,
  rows,
  highlightSongs,
  defaultOpen,
  compact,
}: {
  tier: LikelihoodTier;
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  defaultOpen: boolean;
  compact?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (rows.length === 0) return null;

  return (
    <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3 transition hover:bg-surface-container"
      >
        <div className="flex items-center gap-3">
          <TierBadge tier={tier} />
          <span className="text-sm text-on-surface-variant">
            {rows.length} {rows.length === 1 ? "song" : "songs"}
          </span>
        </div>
        <div className="flex items-center gap-2 text-on-surface-variant">
          <span className="hidden font-label text-[10px] uppercase tracking-[0.14rem] sm:inline">
            {isOpen ? "Collapse" : "Expand"}
          </span>
          <ChevronIcon open={isOpen} />
        </div>
      </button>

      {isOpen && (
        <div className="border-t border-outline-variant/15">
          {/* Desktop table view */}
          <div className="hidden md:block">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr>
                  <th className="px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
                    Rank
                  </th>
                  <th className="px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
                    Song
                  </th>
                  {!compact && (
                    <th className="px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
                      Last Played
                    </th>
                  )}
                  <th className="px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
                    Gap
                  </th>
                  {highlightSongs && (
                    <th className="px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
                      Played
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => {
                  const isHighlighted = highlightSongs?.has(normalizeSongName(row.songName));
                  return (
                    <tr
                      key={`${row.rank}-${row.songName}`}
                      className={`transition-colors hover:bg-surface-container ${
                        index % 2 === 1 ? "bg-surface-container-low/50" : ""
                      } ${isHighlighted ? "bg-green-950/20" : ""}`}
                    >
                      <td className="whitespace-nowrap px-4 py-2.5 font-headline text-sm font-bold tabular-nums text-on-surface-variant">
                        {row.rank}
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`font-headline font-medium ${isHighlighted ? "text-green-300" : "text-on-surface"}`}>
                          {row.songName}
                        </span>
                      </td>
                      {!compact && (
                        <td className="whitespace-nowrap px-4 py-2.5 text-sm text-on-surface-variant">
                          {row.lastPlayed ?? "—"}
                        </td>
                      )}
                      <td className="whitespace-nowrap px-4 py-2.5 font-headline text-sm text-on-surface-variant">
                        {row.currentGap !== null
                          ? `${row.currentGap} ${row.currentGap === 1 ? "show" : "shows"}`
                          : "—"}
                      </td>
                      {highlightSongs && (
                        <td className="px-4 py-2.5">
                          {isHighlighted && <CheckIcon />}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile card view */}
          <div className="divide-y divide-outline-variant/10 md:hidden">
            {rows.map((row) => {
              const isHighlighted = highlightSongs?.has(normalizeSongName(row.songName));
              return (
                <div
                  key={`${row.rank}-${row.songName}`}
                  className={`flex items-center justify-between px-4 py-3 ${isHighlighted ? "bg-green-950/20" : ""}`}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-headline text-sm font-bold tabular-nums text-on-surface-variant">
                      {row.rank}
                    </span>
                    <div>
                      <p className={`font-headline text-sm font-medium ${isHighlighted ? "text-green-300" : "text-on-surface"}`}>
                        {row.songName}
                        {isHighlighted && <span className="ml-2"><CheckIcon /></span>}
                      </p>
                      <p className="text-xs text-on-surface-variant">
                        {row.currentGap !== null
                          ? `${row.currentGap} ${row.currentGap === 1 ? "show" : "shows"} ago`
                          : "Gap unknown"}
                      </p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function SongBoard({ rows, highlightSongs, compact }: Props) {
  const grouped = TIER_ORDER.reduce(
    (acc, tier) => {
      acc[tier] = rows.filter((row) => row.tier === tier);
      return acc;
    },
    {} as Record<LikelihoodTier, PredictionRow[]>,
  );

  return (
    <div className="space-y-3">
      {TIER_ORDER.map((tier) => (
        <TierSection
          key={tier}
          tier={tier}
          rows={grouped[tier]}
          highlightSongs={highlightSongs}
          defaultOpen={tier === "expected" || tier === "hot"}
          compact={compact}
        />
      ))}
      <p className="text-center font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant/50">
        {rows.length} songs ranked · Tiers reflect relative model signal, not guaranteed outcomes
      </p>
    </div>
  );
}
