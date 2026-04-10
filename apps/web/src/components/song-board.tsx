"use client";

import { useState } from "react";

import type { PredictionRow } from "@/lib/data";
import { TIER_ORDER, type LikelihoodTier, type ModelSlug } from "@/lib/config";
import { TierBadge } from "@/components/tier-badge";
import { formatMMDDYYYY } from "@/lib/format";
import { groupPredictionRowsByTier, normalizeSongName } from "@/lib/song-board";

type Props = {
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  secondarySongs?: Set<string>;
  compact?: boolean;
  modelSlug?: ModelSlug | string;
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

type TierSectionProps = {
  tier: LikelihoodTier;
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  secondarySongs?: Set<string>;
  defaultOpen: boolean;
  compact?: boolean;
  modelSlug?: string;
};

type TierRowState = {
  isHighlighted: boolean;
  agreesWithOtherModel: boolean;
};

function getTierRowState(
  row: PredictionRow,
  highlightSongs?: Set<string>,
  secondarySongs?: Set<string>,
): TierRowState {
  const normalizedSongName = normalizeSongName(row.songName);

  return {
    isHighlighted: highlightSongs?.has(normalizedSongName) ?? false,
    agreesWithOtherModel: secondarySongs?.has(normalizedSongName) ?? false,
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

function TierDesktopTable({
  compact,
  highlightSongs,
  isCkPlus,
  rows,
}: {
  compact?: boolean;
  highlightSongs?: Set<string>;
  isCkPlus: boolean;
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
            <th
              className={`px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant ${isCkPlus ? "w-[34%]" : "w-[44%]"}`}
            >
              Song
            </th>
            {!isCkPlus ? (
              <th className="w-32 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
                Plays Last Year
              </th>
            ) : null}
            <th className="w-28 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
              Current Gap
            </th>
            {isCkPlus ? (
              <>
                <th className="w-28 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
                  Avg Gap
                </th>
                <th className="w-28 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
                  Gap Ratio
                </th>
              </>
            ) : null}
            {!compact ? (
              <th className="w-32 px-4 py-2.5 font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant text-right">
                Last Played
              </th>
            ) : null}
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
                {!isCkPlus ? (
                  <td className="whitespace-nowrap px-4 py-3.5 text-right text-sm tabular-nums text-on-surface-variant">
                    {row.playsPastYear !== null ? row.playsPastYear : "—"}
                  </td>
                ) : null}
                <td className="whitespace-nowrap px-4 py-3.5 text-right">
                  <span className="rounded-full bg-surface-container px-2.5 py-1 font-mono text-xs font-medium text-on-surface-variant">
                    {row.currentGap !== null ? row.currentGap : "—"}
                  </span>
                </td>
                {isCkPlus ? (
                  <>
                    <td className="whitespace-nowrap px-4 py-3.5 text-right text-sm tabular-nums text-on-surface-variant">
                      {row.avgGap !== null ? row.avgGap.toFixed(1) : "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3.5 text-right text-sm tabular-nums text-on-surface-variant">
                      {row.gapRatio !== null ? `${row.gapRatio.toFixed(1)}x` : "—"}
                    </td>
                  </>
                ) : null}
                {!compact ? (
                  <td className="whitespace-nowrap px-4 py-3.5 text-right text-sm text-on-surface-variant">
                    {row.lastPlayed ? formatMMDDYYYY(row.lastPlayed) : "—"}
                  </td>
                ) : null}
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
  secondarySongs,
}: {
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  secondarySongs?: Set<string>;
}) {
  return (
    <div className="divide-y divide-outline-variant/10 md:hidden">
      {rows.map((row) => {
        const { isHighlighted, agreesWithOtherModel } = getTierRowState(
          row,
          highlightSongs,
          secondarySongs,
        );

        return (
          <div
            key={`${row.rank}-${row.songName}`}
            className={`flex items-center justify-between px-4 py-4 ${isHighlighted ? "bg-green-950/20" : ""}`}
          >
            <div className="flex items-center gap-3">
              <span className="flex size-8 items-center justify-center rounded-full bg-surface-container-high/60 font-headline text-sm font-bold tabular-nums text-on-surface-variant">
                {row.rank}
              </span>
              <div>
                <p
                  className={`font-headline text-sm font-medium ${isHighlighted ? "text-green-300" : "text-on-surface"}`}
                >
                  {row.songName}
                  {isHighlighted ? (
                    <span className="ml-1">
                      <CheckIcon />
                    </span>
                  ) : null}
                  {agreesWithOtherModel ? (
                    <span className="ml-1">
                      <ModelAgreeIcon />
                    </span>
                  ) : null}
                </p>
                <p className="text-xs text-on-surface-variant">
                  {row.currentGap !== null
                    ? `${row.currentGap} ${row.currentGap === 1 ? "show" : "shows"} ago`
                    : "Current gap unknown"}
                  {row.playsPastYear !== null
                    ? ` · ${row.playsPastYear} play${row.playsPastYear === 1 ? "" : "s"} last year`
                    : ""}
                  {row.lastPlayed ? ` · ${formatMMDDYYYY(row.lastPlayed)}` : ""}
                </p>
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
  secondarySongs,
  defaultOpen,
  compact,
  modelSlug,
}: TierSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (rows.length === 0) return null;

  const isCkPlus = modelSlug === "ckplus";

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
          isCkPlus={isCkPlus}
          rows={rows}
        />
        <TierMobileList
          rows={rows}
          highlightSongs={highlightSongs}
          secondarySongs={secondarySongs}
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

export function SongBoard({ rows, highlightSongs, secondarySongs, compact, modelSlug }: Props) {
  const grouped = groupPredictionRowsByTier(rows);

  return (
    <div className="space-y-4">
      {TIER_ORDER.map((tier) => (
        <TierSection
          key={tier}
          tier={tier}
          rows={grouped[tier]}
          highlightSongs={highlightSongs}
          secondarySongs={secondarySongs}
          defaultOpen
          compact={compact}
          modelSlug={modelSlug}
        />
      ))}
      <p className="pt-2 text-center font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant/55">
        Tiers reflect relative model signal, not guaranteed outcomes
      </p>
    </div>
  );
}
