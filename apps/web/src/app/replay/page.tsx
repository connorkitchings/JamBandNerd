import type { Metadata } from "next";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
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
  formatCompactDateLabel,
  formatDateLabel,
  formatPercent,
  formatTimestampLabel,
} from "@/lib/format";
import {
  computeTopKHits,
  computeTopKRecall,
  normalizeSongName,
} from "@/lib/song-board-core";

export const dynamic = "force-dynamic";

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
    ? ` (${formatCompactDateLabel(params.date)})`
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

  if (accuracyState.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the replay route."
      />
    );
  }

  if (accuracyState.status === "error") {
    return <DataState title="Replay query failed" body={accuracyState.message} />;
  }

  if (accuracyState.status === "empty") {
    return (
      <DataState
        title="No replay history available"
        body="No retained scored shows were found for the selected band."
      />
    );
  }

  const availableShows = accuracyState.rows
    .map((row) => row.showDate)
    .filter((showDate): showDate is string => Boolean(showDate))
    .map((showDate) => ({ showDate }));
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

  if (predictionState.status === "error") {
    return <DataState title="Replay query failed" body={predictionState.message} />;
  }

  if (predictionState.status === "empty") {
    return (
      <DataState
        title="No prediction snapshot available"
        body="A retained scored show was found, but no prediction snapshot was available for that date."
      />
    );
  }

  if (predictionState.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the replay route."
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
  const top10Hits = computeTopKHits(rows, actualSongs, 10);
  const top25Hits = computeTopKHits(rows, actualSongs, 25);
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
        eyebrow="Completed show"
        title={`${bandName} prediction replay`}
        meta={formatDateLabel(selectedDate)}
        description="Review a retained prediction board against the actual setlist for a completed show. Replay uses the saved single-model snapshot for that band and date."
        aside={
          <div className="editorial-panel p-5">
            <ReplayShowSelect
              band={accuracyState.band}
              selectedDate={selectedDate}
              options={availableShows}
            />
            <div className="mt-5 border-t border-outline-variant/15 pt-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Snapshot
              </p>
              <p className="mt-2 text-sm text-on-surface">
                {formatTimestampLabel(predictionState.snapshot.predictedAt)}
              </p>
            </div>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <SectionCard
          title={setlist ? String(setlist.songs.length) : "—"}
          eyebrow="Songs played"
          centered
        />
        <SectionCard
          title={setlist ? `${top10Hits}/10` : "—"}
          eyebrow="Top 10 hits"
          centered
        />
        <SectionCard
          title={setlist ? `${top25Hits}/25` : "—"}
          eyebrow="Top 25 hits"
          centered
        />
      </section>

      <SectionCard title="Show Context">
        <div className="grid gap-3 md:grid-cols-3">
          <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
              Venue
            </p>
            <p className="mt-2 text-sm text-on-surface">
              {show?.venueName ?? "Venue unavailable"}
            </p>
          </div>
          <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
              Location
            </p>
            <p className="mt-2 text-sm text-on-surface">
              {locationLabel ?? "Location unavailable"}
            </p>
          </div>
          <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
              Recall
            </p>
            <p className="mt-2 text-sm text-on-surface">
              Top 10 {formatPercent(computeTopKRecall(rows, actualSongs, 10))}
            </p>
          </div>
        </div>
      </SectionCard>

      <div className="grid gap-6">
        <SectionCard title="Prediction Board" eyebrow="Saved snapshot">
          <SongBoard rows={rows} highlightSongs={actualSongs} compact />
        </SectionCard>

        <SectionCard title="Actual Setlist" eyebrow="Completed show">
          {setlist ? (
            <SetlistColumns songs={setlist.songs} />
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
  );
}
