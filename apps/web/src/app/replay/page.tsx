import type { Metadata } from "next";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { PageHero } from "@/components/page-hero";
import { ReplayShowSelect } from "@/components/replay-show-select";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
} from "@/components/responsive-table";
import { SectionCard } from "@/components/section-card";
import { SetlistColumns } from "@/components/setlist-columns";
import { MODEL_CONFIG } from "@/lib/config";
import {
  bandEntryBySlug,
  getBands,
  getReplaySnapshot,
  resolveBandSelection,
  type PredictionRow,
} from "@/lib/data";
import {
  buildLocationLabel,
  formatCompactDateLabel,
  formatPercent,
} from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    date?: string;
  }>;
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;
  const dateStr = params.date ? ` (${formatCompactDateLabel(params.date)})` : "";

  return {
    title: `${bandName} Replay${dateStr} | JamBandNerd`,
    description: `Review both model boards against the actual setlist for a completed ${bandName} show.`,
  };
}

function normalizeSongName(value: string) {
  return value.trim().toLowerCase();
}

function computeTopKRecall(
  rows: PredictionRow[],
  actualSongs: Set<string>,
  k: number,
) {
  if (actualSongs.size === 0) {
    return null;
  }

  let hits = 0;
  for (let index = 0; index < Math.min(k, rows.length); index += 1) {
    if (actualSongs.has(normalizeSongName(rows[index].songName))) {
      hits += 1;
    }
  }

  return hits / actualSongs.size;
}

function computeTopKHits(
  rows: PredictionRow[],
  actualSongs: Set<string>,
  k: number,
) {
  let hits = 0;
  for (let index = 0; index < Math.min(k, rows.length); index += 1) {
    if (actualSongs.has(normalizeSongName(rows[index].songName))) {
      hits += 1;
    }
  }
  return hits;
}

function wasPlayed(songName: string | null, actualSongs: Set<string>) {
  return songName ? actualSongs.has(normalizeSongName(songName)) : false;
}

export default async function ReplayPage({ searchParams }: Props) {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  if (bandsResult.status === "ready" && bandSelection.isInvalid) {
    return (
      <DataState
        title="Band not found"
        body={`No active band found for slug "${bandSelection.requestedSlug}". Select a supported band from the navigation.`}
      />
    );
  }

  const selectedBand =
    bandsResult.status === "ready" ? bandSelection.bandEntry?.slug : params.band;
  const state = await getReplaySnapshot(selectedBand, params.date, 50);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the replay route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Replay query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No replay history available"
        body="No retained scored prediction runs were found for both models on the selected band."
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;
  const show = state.replay.show;
  const notebookSnapshot = state.replay.snapshots.notebook;
  const ckplusSnapshot = state.replay.snapshots.ckplus;
  const notebookRows = notebookSnapshot?.predictions ?? [];
  const ckplusRows = ckplusSnapshot?.predictions ?? [];
  const actualSongs = new Set(
    (state.replay.setlist?.songs ?? []).map((song) => normalizeSongName(song.songName)),
  );
  const locationLabel = buildLocationLabel([
    show?.city ?? null,
    show?.state ?? show?.country ?? null,
  ]);

  const notebookTop10Hits = computeTopKHits(notebookRows, actualSongs, 10);
  const ckplusTop10Hits = computeTopKHits(ckplusRows, actualSongs, 10);
  const notebookByRank = new Map(notebookRows.map((row) => [row.rank, row] as const));
  const ckplusByRank = new Map(ckplusRows.map((row) => [row.rank, row] as const));
  const maxRank = Math.max(
    notebookRows[notebookRows.length - 1]?.rank ?? 0,
    ckplusRows[ckplusRows.length - 1]?.rank ?? 0,
  );
  const replayRows = Array.from({ length: maxRank }, (_, index) => {
    const rank = index + 1;
    const notebookRow = notebookByRank.get(rank) ?? null;
    const ckplusRow = ckplusByRank.get(rank) ?? null;

    return {
      rank,
      notebookSong: notebookRow?.songName ?? null,
      notebookPlayed: wasPlayed(notebookRow?.songName ?? null, actualSongs),
      ckplusSong: ckplusRow?.songName ?? null,
      ckplusPlayed: wasPlayed(ckplusRow?.songName ?? null, actualSongs),
    };
  });

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav
        band={state.band}
        model="notebook"
        bands={bands}
        pathname="/replay"
        compareHref={null}
        hideSecondary
        bandLinks={bands.map((item) => ({
          href: state.replay.selectedDate
            ? `/replay?band=${item.slug}&date=${state.replay.selectedDate}`
            : `/replay?band=${item.slug}`,
          label: item.displayName,
          active: item.slug === state.band,
        }))}
      />

      <PageHero
        kicker="Replay"
        eyebrow=""
        title={`${bandName} prediction replay`}
        description="Review one completed show with both retained model boards aligned to the same night, then mark what each board captured from the actual setlist."
        descriptionClassName="max-w-4xl"
      />

      <SectionCard title="Actual Setlist">
        {state.replay.setlist ? (
          <div className="space-y-5">
            <ReplayShowSelect
              band={state.band}
              selectedDate={state.replay.selectedDate}
              options={state.replay.availableShows}
              label="Select show"
            />
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Venue
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  {show?.venueName ?? "Unavailable"}
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Location
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  {locationLabel || "Unavailable"}
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Song count
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  {state.replay.setlist.songs.length}
                </p>
              </div>
            </div>
            <SetlistColumns songs={state.replay.setlist.songs} />
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low p-5 text-center">
                <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                  Actual setlist
                </p>
                <p className="mt-4 font-headline text-4xl font-semibold tracking-[-0.04em] text-on-surface">
                  {state.replay.setlist.songs.length}
                </p>
                <p className="mt-1 text-sm text-on-surface">songs played</p>
              </div>
              <div className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low p-5 text-center">
                <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                  Notebook hits
                </p>
                <div className="mt-4 flex items-end justify-center gap-3">
                  <p className="font-headline text-4xl font-semibold tracking-[-0.04em] text-primary">
                    {notebookRows.length > 0 ? notebookTop10Hits : "—"}
                  </p>
                  <p className="pb-1 text-[11px] uppercase tracking-[0.14rem] text-on-surface-variant">
                    top 10
                  </p>
                </div>
                <p className="mt-2 text-sm text-on-surface">
                  {formatPercent(computeTopKRecall(notebookRows, actualSongs, 10))} recall
                </p>
              </div>
              <div className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low p-5 text-center">
                <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                  CK+ hits
                </p>
                <div className="mt-4 flex items-end justify-center gap-3">
                  <p className="font-headline text-4xl font-semibold tracking-[-0.04em] text-tertiary">
                    {ckplusRows.length > 0 ? ckplusTop10Hits : "—"}
                  </p>
                  <p className="pb-1 text-[11px] uppercase tracking-[0.14rem] text-on-surface-variant">
                    top 10
                  </p>
                </div>
                <p className="mt-2 text-sm text-on-surface">
                  {formatPercent(computeTopKRecall(ckplusRows, actualSongs, 10))} recall
                </p>
              </div>
            </div>
          </div>
        ) : (
          <DataState
            title="No setlist found"
            body="A retained replay snapshot exists, but the matching setlist payload was not found."
          />
        )}
      </SectionCard>

      <SectionCard title="Notebook vs CK+">
        {notebookSnapshot && ckplusSnapshot ? (
          <div className="space-y-5">
            <p className="text-sm leading-6 text-on-surface-variant">
              Read both boards by rank and check whether each pick made the actual setlist.
            </p>
            <ResponsiveTableFrame
              minWidthClassName="min-w-[780px]"
              testId="replay-comparison"
            >
              <thead className="bg-surface-container-low text-on-surface-variant">
                <tr>
                  <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap`}>Rank</th>
                  <th className={TABLE_HEAD_CLASS}>{MODEL_CONFIG.notebook.displayName}</th>
                  <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center`}>
                    Played
                  </th>
                  <th className={TABLE_HEAD_CLASS}>{MODEL_CONFIG.ckplus.displayName}</th>
                  <th className={`${TABLE_HEAD_CLASS} whitespace-nowrap text-center`}>
                    Played
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/20 bg-surface-container text-on-surface">
                {replayRows.map((row) => (
                  <tr key={row.rank} className="odd:bg-surface-container-low/30">
                    <td
                      className={`${TABLE_CELL_CLASS} whitespace-nowrap font-headline font-semibold text-on-surface-variant`}
                    >
                      {row.rank}
                    </td>
                    <td className={TABLE_CELL_CLASS}>
                      <span
                        className={`font-headline font-medium ${
                          row.notebookPlayed ? "text-primary" : "text-on-surface"
                        }`}
                      >
                        {row.notebookSong ?? "—"}
                      </span>
                    </td>
                    <td className={`${TABLE_CELL_CLASS} text-center`}>
                      <span
                        className={`font-label text-[10px] font-semibold uppercase tracking-[0.16rem] ${
                          row.notebookSong
                            ? row.notebookPlayed
                              ? "text-primary"
                              : "text-on-surface-variant"
                            : "text-on-surface-variant"
                        }`}
                        aria-label={
                          row.notebookSong
                            ? row.notebookPlayed
                              ? "Notebook prediction was played"
                              : "Notebook prediction was not played"
                            : "No notebook prediction"
                        }
                      >
                        {row.notebookSong ? (row.notebookPlayed ? "✓" : "") : "—"}
                      </span>
                    </td>
                    <td className={TABLE_CELL_CLASS}>
                      <span
                        className={`font-headline font-medium ${
                          row.ckplusPlayed ? "text-tertiary" : "text-on-surface"
                        }`}
                      >
                        {row.ckplusSong ?? "—"}
                      </span>
                    </td>
                    <td className={`${TABLE_CELL_CLASS} text-center`}>
                      <span
                        className={`font-label text-[10px] font-semibold uppercase tracking-[0.16rem] ${
                          row.ckplusSong
                            ? row.ckplusPlayed
                              ? "text-primary"
                              : "text-on-surface-variant"
                            : "text-on-surface-variant"
                        }`}
                        aria-label={
                          row.ckplusSong
                            ? row.ckplusPlayed
                              ? "CK plus prediction was played"
                              : "CK plus prediction was not played"
                            : "No CK plus prediction"
                        }
                      >
                        {row.ckplusSong ? (row.ckplusPlayed ? "✓" : "") : "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </ResponsiveTableFrame>
          </div>
        ) : (
          <DataState
            title="Replay snapshots missing"
            body="This show is in the replay window, but both retained model boards were not available for table comparison."
          />
        )}
      </SectionCard>
    </div>
  );
}
