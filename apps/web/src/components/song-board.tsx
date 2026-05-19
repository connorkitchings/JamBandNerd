"use client";

import { useState } from "react";

import type { PredictionRow } from "@/lib/data";
import { TIER_ORDER, type LikelihoodTier } from "@/lib/config";
import { TierBadge } from "@/components/tier-badge";
import { formatMMDDYYYY } from "@/lib/format";
import { groupPredictionRowsByTier, normalizeSongName } from "@/lib/song-board-core";

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

type TierSectionProps = {
  tier: LikelihoodTier;
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  defaultOpen: boolean;
  compact?: boolean;
};

function getTierRowState(
  row: PredictionRow,
  highlightSongs?: Set<string>,
) {
  return {
    isHighlighted: highlightSongs?.has(normalizeSongName(row.songName)) ?? false,
  };
}

function TierSectionHeader({
  tier,
  rowCount,
  isOpen,
  onExpand,
}: {
  tier: LikelihoodTier;
  rowCount: number;
  isOpen: boolean;
  onExpand: () => void;
}) {
  return (
    <div className="flex w-full items-center justify-between px-4 py-4">
      <div className="flex items-center gap-3">
        <TierBadge tier={tier} />
        <span className="text-sm text-on-surface-variant">
          {rowCount} {rowCount === 1 ? "song" : "songs"}
        </span>
      </div>
      {!isOpen ? (
        <button
          type="button"
          onClick={onExpand}
          aria-expanded={false}
          aria-controls={`tier-content-${tier}`}
          className="flex items-center gap-2 text-on-surface-variant transition hover:text-on-surface focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
        >
          <span className="hidden font-label text-[10px] uppercase tracking-[0.14rem] sm:inline">
            Expand
          </span>
          <ChevronIcon open={false} />
        </button>
      ) : null}
    </div>
  );
}

function ProbabilityBar({ probability }: { probability: number | null }) {
  if (probability === null) return <span className="text-sm tabular-nums text-on-surface-variant">—</span>;
  const pct = Math.round(probability * 1000) / 10;
  const fillPct = Math.min(probability * 100, 100);
  return (
    <div className="relative flex h-6 w-full items-center overflow-hidden rounded-full bg-surface-container">
      <div
        className="absolute inset-y-0 left-0 rounded-full bg-primary/20"
        style={{ width: `${fillPct}%` }}
      />
      <span className="relative w-full pr-2.5 text-right font-mono text-xs font-medium tabular-nums text-on-surface-variant">
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function TierDesktopTable({
  compact,
  highlightSongs,
  rows,
}: {
  compact?: boolean;
  highlightSongs?: Set<string>;
  rows: PredictionRow[];
}) {
  return (
    <div className="hidden w-full overflow-x-auto md:block">
      <table className="w-full table-fixed border-collapse text-left text-sm">
        <thead>
          <tr>
            <th className="w-16 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Rank
            </th>
            <th className="w-[36%] px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant">
              Song
            </th>
            <th className="w-28 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
              Recent Plays
            </th>
            <th className="w-28 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
              Current Gap
            </th>
            {!compact ? (
              <th className="w-32 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
                Last Played
              </th>
            ) : null}
            <th className="w-36 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
              Probability
            </th>
            {highlightSongs ? (
              <th className="w-24 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-center">
                Played
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const { isHighlighted } = getTierRowState(row, highlightSongs);

            return (
              <tr
                key={`${row.rank}-${row.songName}`}
                className={`border-t border-outline-variant/8 transition-colors hover:bg-surface-container-high/20 ${isHighlighted ? "bg-green-950/20" : ""}`}
              >
                <td className="whitespace-nowrap px-4 py-3.5 font-headline text-sm font-bold tabular-nums text-on-surface-variant">
                  {row.rank}
                </td>
                <td className="px-4 py-3.5">
                  <span
                    className={`block truncate font-headline font-medium ${isHighlighted ? "text-green-300" : "text-on-surface"}`}
                    title={row.songName}
                  >
                    {row.songName}
                  </span>
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 text-right text-sm tabular-nums text-on-surface-variant">
                  {row.recentPlays50 !== null ? `${row.recentPlays50} / 50` : "—"}
                </td>
                <td className="whitespace-nowrap px-4 py-3.5 text-right">
                  <span className="rounded-full bg-surface-container px-2.5 py-1 font-mono text-xs font-medium text-on-surface-variant">
                    {row.currentGap !== null ? row.currentGap : "—"}
                  </span>
                </td>
                {!compact ? (
                  <td className="whitespace-nowrap px-4 py-3.5 text-right text-sm text-on-surface-variant">
                    {row.lastPlayed ? formatMMDDYYYY(row.lastPlayed) : "—"}
                  </td>
                ) : null}
                <td className="px-4 py-3.5">
                  <ProbabilityBar probability={row.probability} />
                </td>
                {highlightSongs ? (
                  <td className="px-4 py-3.5 text-center">{isHighlighted ? <CheckIcon /> : null}</td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TierMobileList({
  rows,
  highlightSongs,
}: {
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
}) {
  return (
    <div className="divide-y divide-outline-variant/10 md:hidden">
      {rows.map((row) => {
        const { isHighlighted } = getTierRowState(row, highlightSongs);
        const firstLine = [
          row.currentGap !== null
            ? `Gap ${row.currentGap}`
            : "Gap unknown",
          row.lastPlayed ? `LTP ${formatMMDDYYYY(row.lastPlayed)}` : null,
          row.recentPlays50 !== null ? `${row.recentPlays50} / 50` : null,
        ].filter(Boolean);
        const probabilityPct =
          row.probability !== null
            ? Math.min(Math.max(row.probability * 100, 0), 100)
            : null;

        return (
          <div
            key={`${row.rank}-${row.songName}`}
            className={`flex items-start gap-3 px-4 py-4 ${isHighlighted ? "bg-green-950/20" : ""}`}
          >
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-surface-container-high/60 font-headline text-sm font-bold tabular-nums text-on-surface-variant">
              {row.rank}
            </span>
            <div className="min-w-0 flex-1">
              <p
                className={`truncate font-headline text-sm font-medium ${isHighlighted ? "text-green-300" : "text-on-surface"}`}
                title={row.songName}
              >
                {row.songName}
                {isHighlighted ? (
                  <span className="ml-1 inline-flex align-middle">
                    <CheckIcon />
                  </span>
                ) : null}
              </p>
              <p className="mt-1 truncate font-label text-[10px] uppercase tracking-[0.12rem] text-on-surface-variant">
                {firstLine.join(" · ")}
              </p>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-container-high">
                  <div
                    className="h-full rounded-full bg-primary/75"
                    style={{ width: `${probabilityPct ?? 0}%` }}
                  />
                </div>
                <span className="w-12 shrink-0 text-right font-mono text-[11px] tabular-nums text-primary/90">
                  {probabilityPct !== null ? `${probabilityPct.toFixed(1)}%` : "—"}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function TierSection({
  tier,
  rows,
  highlightSongs,
  defaultOpen,
  compact,
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
        />
        <TierMobileList
          rows={rows}
          highlightSongs={highlightSongs}
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

export function SongBoard({ rows, highlightSongs, compact }: Props) {
  const grouped = groupPredictionRowsByTier(rows);

  return (
    <div className="space-y-4">
      {TIER_ORDER.map((tier) => (
        <TierSection
          key={tier}
          tier={tier}
          rows={grouped[tier]}
          highlightSongs={highlightSongs}
          defaultOpen
          compact={compact}
        />
      ))}
      <p className="pt-2 text-center font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant/55">
        Tiers reflect relative model signal, not guaranteed outcomes
      </p>
    </div>
  );
}
