import type { Metadata } from "next";
import Link from "next/link";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";
import { SetlistTable } from "@/components/setlist-table";
import { SongBoard } from "@/components/song-board";
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
  formatDateLabel,
  formatPercent,
  formatTimestampLabel,
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
  const notebookSongs = new Set(
    notebookRows.map((row) => normalizeSongName(row.songName)),
  );
  const ckplusSongs = new Set(
    ckplusRows.map((row) => normalizeSongName(row.songName)),
  );
  const actualSongs = new Set(
    (state.replay.setlist?.songs ?? []).map((song) => normalizeSongName(song.songName)),
  );
  const locationLabel = buildLocationLabel([
    show?.city ?? null,
    show?.state ?? show?.country ?? null,
  ]);
  const showMeta = [
    formatDateLabel(state.replay.selectedDate),
    show?.venueName ?? null,
    locationLabel,
  ]
    .filter(Boolean)
    .join(" • ");

  const notebookTop10Hits = computeTopKHits(notebookRows, actualSongs, 10);
  const ckplusTop10Hits = computeTopKHits(ckplusRows, actualSongs, 10);

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
        eyebrow="Historical review"
        title={`${bandName} prediction replay`}
        meta={showMeta}
        description="Review one completed show with both retained model boards aligned to the same night, then mark what each board captured from the actual setlist."
        aside={
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <div className="editorial-panel p-5 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Actual setlist
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-on-surface">
                {state.replay.setlist?.songs.length ?? 0}
              </p>
              <p className="mt-1 text-[10px] font-medium text-on-surface-variant">
                logged songs
              </p>
            </div>
            <div className="editorial-panel p-5 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Notebook Top 10
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-primary">
                {notebookRows.length > 0 ? `${notebookTop10Hits} hits` : "—"}
              </p>
              <p className="mt-1 text-[10px] font-medium text-on-surface-variant">
                {formatPercent(computeTopKRecall(notebookRows, actualSongs, 10))}
              </p>
            </div>
            <div className="editorial-panel p-5 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                CK+ Top 10
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-tertiary">
                {ckplusRows.length > 0 ? `${ckplusTop10Hits} hits` : "—"}
              </p>
              <p className="mt-1 text-[10px] font-medium text-on-surface-variant">
                {formatPercent(computeTopKRecall(ckplusRows, actualSongs, 10))}
              </p>
            </div>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.78fr)_minmax(0,1.22fr)]">
        <SectionCard
          title="Select Show"
          eyebrow={`${state.replay.availableShows.length} replayable nights`}
        >
          <div className="space-y-4">
            <p className="text-sm leading-6 text-on-surface-variant">
              Browse the retained replay window for this band. Each show here has stored historical runs for both models.
            </p>
            <div className="overflow-x-auto rounded-xl border border-outline-variant/20 bg-surface-container-low [-webkit-overflow-scrolling:touch] [scrollbar-gutter:stable]">
              <div className="flex gap-2 px-3 py-3 sm:flex-wrap sm:px-3 sm:py-2">
                {state.replay.availableShows.map((showOption) => (
                  <Link
                    key={showOption.showDate}
                    href={`/replay?band=${state.band}&date=${showOption.showDate}`}
                    className={`touch-manipulation flex-shrink-0 rounded-full border px-4 py-2 font-headline text-xs uppercase tracking-[0.14rem] transition sm:flex-shrink ${
                      showOption.showDate === state.replay.selectedDate
                        ? "border-primary bg-primary-container text-white"
                        : "border-outline-variant bg-surface text-on-surface-variant hover:border-primary hover:text-on-surface"
                    }`}
                  >
                    {formatCompactDateLabel(showOption.showDate)}
                  </Link>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Selected night
              </p>
              <p className="mt-2 font-headline text-lg font-medium text-on-surface">
                {formatDateLabel(state.replay.selectedDate)}
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                {show?.venueName
                  ? `${show.venueName}${locationLabel ? ` • ${locationLabel}` : ""}`
                  : "Show details unavailable"}
              </p>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Actual Setlist" eyebrow={state.replay.selectedDate ?? "No date"}>
          {state.replay.setlist ? (
            <div className="space-y-5">
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
              <SetlistTable songs={state.replay.setlist.songs} />
            </div>
          ) : (
            <DataState
              title="No setlist found"
              body="A retained replay snapshot exists, but the matching setlist payload was not found."
            />
          )}
        </SectionCard>
      </div>

      <div className="grid gap-6 2xl:grid-cols-2">
        <SectionCard
          title={MODEL_CONFIG.notebook.displayName}
          eyebrow={notebookSnapshot?.referenceDate ?? "No snapshot date"}
        >
          {notebookSnapshot ? (
            <div className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                    Prediction run
                  </p>
                  <p className="mt-2 text-sm text-on-surface">
                    {formatTimestampLabel(notebookSnapshot.predictedAt)}
                  </p>
                </div>
                <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                    Top 10 accuracy
                  </p>
                  <p className="mt-2 text-sm text-on-surface">
                    {formatPercent(computeTopKRecall(notebookRows, actualSongs, 10))}
                  </p>
                </div>
                <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                    Captured songs
                  </p>
                  <p className="mt-2 text-sm text-on-surface">
                    {notebookTop10Hits} in Top 10
                  </p>
                </div>
              </div>
              <SongBoard
                rows={notebookRows}
                highlightSongs={actualSongs}
                secondarySongs={ckplusSongs}
                compact
                modelSlug="notebook"
              />
            </div>
          ) : (
            <DataState
              title="Notebook snapshot missing"
              body="This show is in the replay window, but the retained Notebook board was not found."
            />
          )}
        </SectionCard>

        <SectionCard
          title={MODEL_CONFIG.ckplus.displayName}
          eyebrow={ckplusSnapshot?.referenceDate ?? "No snapshot date"}
        >
          {ckplusSnapshot ? (
            <div className="space-y-5">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                    Prediction run
                  </p>
                  <p className="mt-2 text-sm text-on-surface">
                    {formatTimestampLabel(ckplusSnapshot.predictedAt)}
                  </p>
                </div>
                <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                    Top 10 accuracy
                  </p>
                  <p className="mt-2 text-sm text-on-surface">
                    {formatPercent(computeTopKRecall(ckplusRows, actualSongs, 10))}
                  </p>
                </div>
                <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                    Captured songs
                  </p>
                  <p className="mt-2 text-sm text-on-surface">
                    {ckplusTop10Hits} in Top 10
                  </p>
                </div>
              </div>
              <SongBoard
                rows={ckplusRows}
                highlightSongs={actualSongs}
                secondarySongs={notebookSongs}
                compact
                modelSlug="ckplus"
              />
            </div>
          ) : (
            <DataState
              title="CK+ snapshot missing"
              body="This show is in the replay window, but the retained CK+ board was not found."
            />
          )}
        </SectionCard>
      </div>
    </div>
  );
}
