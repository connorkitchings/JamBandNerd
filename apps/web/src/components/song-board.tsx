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

// Wide: rank | song | tier | probability | caret. At 720px and below the badge and
// probability drop under the song name, in the same column.
const ROW_GRID =
  "grid grid-cols-[2rem_minmax(0,1fr)_1.5rem] items-center gap-x-3 gap-y-1 " +
  "min-[721px]:grid-cols-[2.5rem_minmax(0,1fr)_6rem_11rem_1.5rem]";

function ProbabilityCell({ probability }: { probability: number | null }) {
  if (probability === null) {
    return <span className="text-sm text-on-surface-variant">—</span>;
  }
  const pct = Math.min(Math.max(probability * 100, 0), 100);
  return (
    <div className="flex items-center gap-3">
      <div aria-hidden="true" className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-container-high">
        <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-14 shrink-0 text-right text-sm font-semibold tabular-nums text-on-surface">
        {pct.toFixed(1)}%
      </span>
    </div>
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
  tier,
  isHighlighted,
  compact,
}: {
  row: PredictionRow;
  tier: LikelihoodTier;
  isHighlighted: boolean;
  compact?: boolean;
}) {
  return (
    <details className={`group border-t border-line ${isHighlighted ? "bg-teal-bg" : ""}`}>
      <summary
        className={`${ROW_GRID} min-h-11 cursor-pointer list-none px-4 py-3 hover:bg-surface-container [&::-webkit-details-marker]:hidden`}
      >
        <span className="col-start-1 row-span-3 row-start-1 self-start text-sm font-bold tabular-nums text-on-surface-variant min-[721px]:row-span-1 min-[721px]:self-center">
          {row.rank}
        </span>
        <span className="col-start-2 row-start-1 flex min-w-0 flex-wrap items-center gap-x-3 font-medium text-on-surface">
          <span className="truncate" title={row.songName}>
            {row.songName}
          </span>
          {isHighlighted ? <PlayedMarker /> : null}
        </span>
        <span className="col-start-2 row-start-2 justify-self-start min-[721px]:col-start-3 min-[721px]:row-start-1">
          <TierBadge tier={tier} />
        </span>
        <span className="col-start-2 col-end-4 row-start-3 min-[721px]:col-start-4 min-[721px]:col-end-5 min-[721px]:row-start-1">
          <ProbabilityCell probability={row.probability} />
        </span>
        <svg
          aria-hidden="true"
          className="col-start-3 row-start-1 size-4 justify-self-end text-on-surface-variant transition-transform group-open:rotate-180 min-[721px]:col-start-5"
          fill="none"
          viewBox="0 0 24 24"
        >
          <path d="M6 9L12 15L18 9" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.75" />
        </svg>
      </summary>
      <dl className="grid grid-cols-2 gap-4 px-4 pb-4 pt-1 min-[721px]:grid-cols-3 min-[721px]:pl-[4.25rem]">
        <Detail label="Shows since played" value={row.currentGap !== null ? String(row.currentGap) : "—"} />
        {!compact ? (
          <Detail label="Last played" value={row.lastPlayed ? formatMMDDYYYY(row.lastPlayed) : "—"} />
        ) : null}
        <Detail label="Plays, last 50 shows" value={row.recentPlays50 !== null ? `${row.recentPlays50} / 50` : "—"} />
      </dl>
    </details>
  );
}

function TierSection({
  tier,
  rows,
  highlightSongs,
  compact,
}: {
  tier: LikelihoodTier;
  rows: PredictionRow[];
  highlightSongs?: Set<string>;
  compact?: boolean;
}) {
  if (rows.length === 0) return null;

  return (
    <section className="overflow-hidden rounded-xl border border-line bg-surface">
      <div className="flex items-center gap-3 px-4 py-3">
        <TierBadge tier={tier} />
        <span className="text-sm text-on-surface-variant">
          {rows.length} {rows.length === 1 ? "song" : "songs"}
        </span>
      </div>
      {rows.map((row) => (
        <SongRow
          key={`${row.rank}-${row.songName}`}
          row={row}
          tier={tier}
          isHighlighted={highlightSongs?.has(normalizeSongName(row.songName)) ?? false}
          compact={compact}
        />
      ))}
    </section>
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
          compact={compact}
        />
      ))}
      <p className="pt-2 text-center text-xs text-on-surface-variant">
        Groups reflect model rank: Prime 1-10 · Likely 11-25 · Possible 26-50
      </p>
    </div>
  );
}
