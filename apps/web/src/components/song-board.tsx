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

const ROW_GRID = "grid grid-cols-[2.25rem_minmax(0,1fr)_auto_1.5rem] items-center gap-x-3";

const TIER_RANGE: Record<LikelihoodTier, string> = {
  prime: "1-10",
  likely: "11-25",
  possible: "26-50",
};

function Probability({ probability }: { probability: number | null }) {
  if (probability === null) {
    return <span className="text-sm text-on-surface-variant">—</span>;
  }
  const pct = Math.min(Math.max(probability * 100, 0), 100);
  return (
    <span className="text-right text-sm font-semibold tabular-nums text-on-surface">{pct.toFixed(1)}%</span>
  );
}

function PlayedMarker() {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal">
      <span aria-hidden="true" className="size-2 rounded-full bg-teal" />
      Played
    </span>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">{label}</dt>
      <dd className="mt-0.5 text-sm tabular-nums text-on-surface">{value}</dd>
    </div>
  );
}

function SongRow({
  row,
  isHighlighted,
  compact,
}: {
  row: PredictionRow;
  isHighlighted: boolean;
  compact?: boolean;
}) {
  return (
    <details className={`group border-t border-line ${isHighlighted ? "bg-teal-bg" : ""}`}>
      <summary
        className={`${ROW_GRID} min-h-11 cursor-pointer list-none px-4 py-3 hover:bg-surface-container [&::-webkit-details-marker]:hidden`}
      >
        <span className="text-sm font-bold tabular-nums text-on-surface-variant">{row.rank}</span>
        <span className="flex min-w-0 flex-wrap items-center gap-x-3 font-medium text-on-surface">
          <span className="truncate" title={row.songName}>
            {row.songName}
          </span>
          {isHighlighted ? <PlayedMarker /> : null}
        </span>
        <Probability probability={row.probability} />
        <svg
          aria-hidden="true"
          className="size-4 justify-self-end text-on-surface-variant transition-transform group-open:rotate-180"
          fill="none"
          viewBox="0 0 24 24"
        >
          <path d="M6 9L12 15L18 9" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" />
        </svg>
      </summary>
      <dl className="grid grid-cols-2 gap-4 px-4 pb-4 pt-1 min-[721px]:grid-cols-3 min-[721px]:pl-[3.5rem]">
        <Detail label="Shows since played" value={row.currentGap !== null ? String(row.currentGap) : "—"} />
        {!compact ? (
          <Detail label="Last played" value={row.lastPlayed ? formatMMDDYYYY(row.lastPlayed) : "—"} />
        ) : null}
        <Detail label="Plays, last 50 shows" value={row.recentPlays50 !== null ? `${row.recentPlays50} / 50` : "—"} />
      </dl>
    </details>
  );
}

function TierDivider({ tier, count }: { tier: LikelihoodTier; count: number }) {
  return (
    <h3 className="flex items-center gap-3 border-t border-line bg-surface-container px-4 py-2 first:border-t-0">
      <TierBadge tier={tier} />
      <span className="text-sm font-normal text-on-surface-variant">
        {count} {count === 1 ? "song" : "songs"} · ranks {TIER_RANGE[tier]}
      </span>
    </h3>
  );
}

export function SongBoard({ rows, highlightSongs, compact }: Props) {
  const grouped = groupPredictionRowsByTier(rows);

  return (
    <div className="space-y-4">
      <section className="overflow-hidden rounded-xl border border-line bg-surface">
        {TIER_ORDER.map((tier) =>
          grouped[tier].length === 0 ? null : (
            <div key={tier}>
              <TierDivider tier={tier} count={grouped[tier].length} />
              {grouped[tier].map((row) => (
                <SongRow
                  key={`${row.rank}-${row.songName}`}
                  row={row}
                  isHighlighted={highlightSongs?.has(normalizeSongName(row.songName)) ?? false}
                  compact={compact}
                />
              ))}
            </div>
          ),
        )}
      </section>
      <p className="pt-2 text-center text-xs text-on-surface-variant">
        Groups reflect model rank: Prime 1-10 · Likely 11-25 · Possible 26-50
      </p>
    </div>
  );
}
