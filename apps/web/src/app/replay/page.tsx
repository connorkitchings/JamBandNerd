import type { Metadata } from "next";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataGate } from "@/components/data-gate";
import { DataState } from "@/components/data-state";
import { PageHero } from "@/components/page-hero";
import { ReplayShowSelect } from "@/components/replay-show-select";
import { SectionCard } from "@/components/section-card";
import { SetlistColumns } from "@/components/setlist-columns";
import { SongBoard } from "@/components/song-board";
import {
  bandEntryBySlug,
  getBands,
  getPredictionsForDate,
  getRecentAccuracy,
  getSetlistForDate,
  getShowDetailsByDate,
  resolveBandSelection,
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

export const revalidate = 3600;

type Props = {
  searchParams: Promise<{
    band?: string;
    date?: string;
  }>;
};

export async function generateMetadata({
  searchParams,
}: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName =
    bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;
  const dateLabel = params.date
    ? ` (${formatMMDDYYYY(params.date)})`
    : "";

  return {
    title: `${bandName} Replay${dateLabel} | JamBandNerd`,
    description: `Review a retained ${bandName} prediction board against the actual setlist for a completed show.`,
  };
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
  const accuracyState = await getRecentAccuracy(selectedBand, 50);

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
    availableShows.some((show) => show.showDate === params.date)
      ? params.date
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

  const bandEntry = bandEntryBySlug(bands, accuracyState.band);
  const bandName = bandEntry?.displayName ?? accuracyState.band;
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

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav
        band={accuracyState.band}
        bands={bands}
        pathname="/replay"
      />

      <PageHero
        kicker="Replay"
        title={
          <>
            {bandName}
            <br />
            <span className="text-primary">prediction replay</span>
          </>
        }
        description="Review a retained prediction board against the actual setlist for a completed show."
        aside={
          <div className="editorial-panel p-5">
            <ReplayShowSelect
              band={accuracyState.band}
              selectedDate={selectedDate}
              options={availableShows}
            />
          </div>
        }
      />

      {setlist ? (
        <SectionCard
          title="Completed Setlist"
          headerAccessory={
            <div className="rounded-full border border-outline-variant/15 bg-surface/50 px-4 py-2 text-center font-headline text-base font-semibold tracking-[0.08em] text-amber-400">
              {formatMMDDYYYY(selectedDate)}
            </div>
          }
        >
          <div className="mb-5 grid gap-3 text-center md:text-left md:grid-cols-3">
            <div className="rounded-xl border border-outline-variant/15 bg-surface-container-low/60 p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Venue
              </p>
              <p className="mt-2 text-sm font-medium text-on-surface">
                {show?.venueName ?? "—"}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/15 bg-surface-container-low/60 p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Location
              </p>
              <p className="mt-2 text-sm font-medium text-on-surface">
                {locationLabel ?? "—"}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/15 bg-surface-container-low/60 p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Songs played
              </p>
              <p className="mt-2 text-sm font-medium text-on-surface">
                {String(setlist.songs.length)}
              </p>
            </div>
          </div>
          <SetlistColumns songs={setlist.songs} highlightSongs={predictedSongs} />
        </SectionCard>
      ) : (
        <SectionCard title="Actual Completed Setlist">
          <DataState
            title="No setlist found"
            body="A retained prediction snapshot exists, but the matching setlist payload was not found."
            headingLevel="h2"
          />
        </SectionCard>
      )}

      {setlist && (
        <div className="grid gap-3 md:grid-cols-3">
          {[
            { k: 10, hits: computeTopKHits(rows, actualSongs, 10), recall: computeTopKRecall(rows, actualSongs, 10) },
            { k: 25, hits: computeTopKHits(rows, actualSongs, 25), recall: computeTopKRecall(rows, actualSongs, 25) },
            { k: 50, hits: computeTopKHits(rows, actualSongs, 50), recall: computeTopKRecall(rows, actualSongs, 50) },
          ].map((metric) => (
            <div
              key={metric.k}
              className="rounded-xl border border-outline-variant/15 bg-surface/35 px-3 py-3 text-center md:px-4"
            >
              <div className="border-b border-outline-variant/15 pb-2">
                <p className="font-headline text-base font-bold text-on-surface underline decoration-current decoration-2 underline-offset-4 md:text-lg">
                  Top {metric.k}
                </p>
              </div>

              <div className="mt-3 grid grid-cols-2 gap-2 md:gap-3">
                <div className="rounded-lg bg-surface-container-low/55 px-2.5 py-2.5 md:rounded-xl md:px-3">
                  <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-tertiary">
                    Hits
                  </p>
                  <p className="mt-0.5 font-headline text-2xl font-bold leading-none text-tertiary md:text-3xl">
                    {metric.hits}
                  </p>
                  <p className="mt-1 text-[11px] leading-4 text-on-surface-variant md:text-xs md:leading-5">
                    picks played
                  </p>
                </div>
                <div className="rounded-lg bg-surface-container-low/55 px-2.5 py-2.5 md:rounded-xl md:px-3">
                  <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-primary">
                    Coverage
                  </p>
                  <p className="mt-0.5 font-headline text-2xl font-bold leading-none text-primary md:text-3xl">
                    {formatPercent(metric.recall)}
                  </p>
                  <p className="mt-1 text-[11px] leading-4 text-on-surface-variant md:text-xs md:leading-5">
                    setlist caught
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-6">
        <SectionCard title="Prediction Board">
          <SongBoard rows={rows} highlightSongs={actualSongs} />
        </SectionCard>
      </div>
    </div>
  );
}
