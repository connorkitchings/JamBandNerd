import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataGate } from "@/components/data-gate";
import { DataState } from "@/components/data-state";
import { MetricCard } from "@/components/metric-card";
import { PerformanceChartPanel } from "@/components/performance-chart-panel";
import { PageSkeleton } from "@/components/page-skeleton";
import { ReplayShowSelect } from "@/components/replay-show-select";
import { SectionCard } from "@/components/section-card";
import { SetlistColumns } from "@/components/setlist-columns";
import { SongBoard } from "@/components/song-board";
import {
  getPredictionsForDate,
  getRecentAccuracy,
  getSetlistForDate,
  getShowDetailsByDate,
  resolveBandPage,
} from "@/lib/data";
import {
  buildLocationLabel,
  formatMMDDYYYY,
  formatPercent,
} from "@/lib/format";
import {
  computeTopKHits,
  computeTopKRecall,
  normalizeSongName,
} from "@/lib/song-board-core";
import { getEasternTodayIso } from "@/lib/show-status";

type Props = {
  params: Promise<{ band: string; date?: string[] }>;
};

// The band segment is prerendered by the parent layout; only the bare
// `/<band>/replay` (latest show) is prerendered. Dated replays render on demand.
export async function generateStaticParams() {
  return [{ date: [] }];
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { band, date } = await params;
  const { bandEntry } = await resolveBandPage(band);
  const requestedDate = date?.[0];
  const dateLabel = requestedDate ? ` (${formatMMDDYYYY(requestedDate)})` : "";

  return {
    title: `${bandEntry.displayName} Replay${dateLabel} | JamBandNerd`,
    description: `Review a retained ${bandEntry.displayName} prediction board against the actual setlist for a completed show.`,
  };
}

export default async function ReplayPage({ params }: Props) {
  const { band, date } = await params;
  const { bandEntry, bands } = await resolveBandPage(band);
  // The layout has already rejected malformed date segments.
  const requestedDate = date?.[0];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav band={band} bands={bands} page="replay" />
      <Suspense fallback={<PageSkeleton />}>
        <ReplayContent
          band={band}
          bandName={bandEntry.displayName}
          requestedDate={requestedDate}
        />
      </Suspense>
    </div>
  );
}

async function ReplayContent({
  band,
  bandName,
  requestedDate,
}: {
  band: string;
  bandName: string;
  requestedDate: string | undefined;
}) {
  // The replay window is keyed on today's date, so it is resolved per request.
  await connection();
  const accuracyState = await getRecentAccuracy(band, 50, getEasternTodayIso());

  if (accuracyState.status !== "ready") {
    return (
      <DataGate
        state={accuracyState}
        missingEnvBody="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the replay route."
        errorTitle="Replay query failed"
        emptyTitle="No replay history available"
        emptyBody="No retained scored shows were found for the selected band."
      />
    );
  }

  const availableShows = [
    ...new Set(
      accuracyState.rows
        .map((row) => row.showDate)
        .filter((showDate): showDate is string => Boolean(showDate)),
    ),
  ].map((showDate) => ({ showDate }));
  const selectedDate =
    availableShows.some((show) => show.showDate === requestedDate)
      ? requestedDate
      : availableShows[0]?.showDate;

  if (!selectedDate) {
    return (
      <DataState
        title="No replay dates available"
        body="The retained replay window did not include dated accuracy rows."
      />
    );
  }

  const [predictionState, showState, setlist] = await Promise.all([
    getPredictionsForDate(accuracyState.band, selectedDate),
    getShowDetailsByDate(accuracyState.band, selectedDate),
    getSetlistForDate(accuracyState.band, selectedDate),
  ]);

  if (predictionState.status !== "ready") {
    return (
      <DataGate
        state={predictionState}
        missingEnvBody="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the replay route."
        errorTitle="Replay query failed"
        emptyTitle="No prediction snapshot available"
        emptyBody="A retained scored show was found, but no prediction snapshot was available for that date."
      />
    );
  }

  const show = showState.status === "ready" ? showState.show : null;
  const actualSongs = new Set(
    (setlist?.songs ?? []).map((song) => normalizeSongName(song.songName)),
  );
  const rows = predictionState.snapshot.predictions;
  const predictedSongs = new Set(
    rows.map((row) => normalizeSongName(row.songName)),
  );
  const locationLabel = buildLocationLabel([
    show?.city ?? null,
    show?.state ?? show?.country ?? null,
  ]);

  const metrics = setlist
    ? ([10, 25, 50] as const).map((k) => ({
        k,
        hits: computeTopKHits(rows, actualSongs, k),
        recall: computeTopKRecall(rows, actualSongs, k),
      }))
    : [];
  const venueLine = [show?.venueName, locationLabel].filter(Boolean).join(" · ");

  return (
    <>
      <section className="editorial-panel flex flex-wrap items-end justify-between gap-6 p-5 md:p-6">
        <div className="min-w-0 flex-1 basis-80">
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-accent-text">
            {bandName} · Replay
          </p>
          <h1 className="mt-2 text-3xl font-bold tabular-nums text-on-surface md:text-4xl">
            {formatMMDDYYYY(selectedDate)}
          </h1>
          <p className="mt-2 text-sm text-on-surface-variant">
            {venueLine || "Venue unavailable"}
            {setlist ? ` · ${setlist.songs.length} songs played` : ""}
          </p>
        </div>
        <ReplayShowSelect
          band={accuracyState.band}
          selectedDate={selectedDate}
          options={availableShows}
        />
      </section>

      {metrics.length > 0 && (
        <section aria-label="Show score" className="grid gap-4 md:grid-cols-3">
          {metrics.map((metric) => (
            <MetricCard
              key={metric.k}
              label={`Top ${metric.k} coverage`}
              value={formatPercent(metric.recall)}
              hint={`${metric.hits} of ${metric.k} picks played`}
              tone="accent"
            />
          ))}
        </section>
      )}

      <div className="flex flex-wrap gap-4">
        <div className="min-w-0 flex-1 basis-[28rem]">
          <SectionCard title="Prediction Board">
            <SongBoard rows={rows} highlightSongs={actualSongs} />
          </SectionCard>
        </div>
        <div className="min-w-0 flex-1 basis-[28rem]">
          <SectionCard title="Completed Setlist">
            {setlist ? (
              <SetlistColumns songs={setlist.songs} highlightSongs={predictedSongs} />
            ) : (
              <DataState
                title="No setlist found"
                body="A retained prediction snapshot exists, but the matching setlist payload was not found."
                headingLevel="h2"
              />
            )}
          </SectionCard>
        </div>
      </div>

      <section className="editorial-panel p-5 md:p-6">
        <h2 className="text-xl font-bold text-on-surface">Recall over recent shows</h2>
        <p className="mb-5 mt-1 text-sm text-on-surface-variant">
          How much of each setlist the top-ranked picks captured. Oldest show on the left.
        </p>
        <PerformanceChartPanel rows={accuracyState.rows} />
      </section>
    </>
  );
}
