import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataGate } from "@/components/data-gate";
import { LiveTracker } from "@/components/live-tracker";
import { PageSkeleton } from "@/components/page-skeleton";
import { PredictionHero, PredictionHeroMetrics } from "@/components/prediction-hero";
import { SharePredictionsButton } from "@/components/share-predictions-button";
import { SongBoard } from "@/components/song-board";
import { SongSearch } from "@/components/song-search";
import { bandPath } from "@/lib/band-routes";
import {
  getLatestPredictions,
  getNextShowDetails,
  getRecentAccuracy,
  getRecentMissingSetlistShows,
  getShowDetailsByDate,
  resolveBandPage,
} from "@/lib/data";
import {
  average,
  buildLocationLabel,
  formatCompactDateLabel,
  formatDateLabel,
  formatAvgHits,
  formatPercent,
  formatTimestampLabel,
} from "@/lib/format";
import { formatTop10Text } from "@/lib/format-predictions-text";
import {
  getDataClock,
  getPredictionDisplayState,
  getPredictionStatusLabel,
  isShowTonight,
} from "@/lib/show-status";

type Props = {
  params: Promise<{ band: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { band, bandEntry } = await resolveBandPage((await params).band);
  const bandName = bandEntry.displayName;

  const title = `${bandName} Setlist Predictions | JamBandNerd`;
  const description = `Latest setlist predictions for ${bandName}, ranked by likelihood tier.`;
  const url = `https://jambandnerd.com${bandPath(band, "predictions")}`;

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      url,
      siteName: "JamBandNerd",
      images: [{ url: "/logo.png", width: 1200, height: 630, alt: title }],
      type: "website",
    },
  };
}

export default async function PredictionsPage({ params }: Props) {
  const { band, bandEntry, bands } = await resolveBandPage((await params).band);

  return (
    <div className="mx-auto w-full max-w-6xl">
      <DashboardSideNav band={band} bands={bands} page="predictions" />
      <Suspense fallback={<PageSkeleton />}>
        <PredictionsContent band={band} bandName={bandEntry.displayName} />
      </Suspense>
    </div>
  );
}

/** Hero accuracy cards; streamed in after the prediction hero so they never delay it. */
async function PredictionAccuracyMetrics({ band, todayIso }: { band: string; todayIso: string }) {
  const accuracyState = await getRecentAccuracy(band, 50, todayIso);
  const accuracyRows = accuracyState.status === "ready" ? accuracyState.rows : [];
  const precisionCards = [
    {
      title: "Top 10",
      avgHits: formatAvgHits(average(accuracyRows.map((row) => row.p10)), 10),
      coverage: formatPercent(average(accuracyRows.map((row) => row.recall10))),
    },
    {
      title: "Top 25",
      avgHits: formatAvgHits(average(accuracyRows.map((row) => row.p25)), 25),
      coverage: formatPercent(average(accuracyRows.map((row) => row.recall25))),
    },
    {
      title: "Top 50",
      avgHits: formatAvgHits(average(accuracyRows.map((row) => row.p50)), 50),
      coverage: formatPercent(average(accuracyRows.map((row) => row.recall50))),
    },
  ] as const;

  return (
    <PredictionHeroMetrics
      performanceWindowLabel="last 50 shows"
      precisionCards={precisionCards}
    />
  );
}

function AccuracyMetricsFallback() {
  return (
    <div
      aria-hidden="true"
      className="editorial-panel relative z-20 mx-auto -mt-6 mb-5 h-32 w-full max-w-6xl animate-pulse px-1 md:-mt-8 md:mb-6"
    />
  );
}

async function PredictionsContent({ band, bandName }: { band: string; bandName: string }) {
  // Show status depends on the current time, so this part renders per request.
  await connection();
  const clock = getDataClock();
  const predictionState = await getLatestPredictions(band, clock.todayIso);

  if (predictionState.status !== "ready") {
    return (
      <DataGate
        state={predictionState}
        className="mx-auto max-w-6xl"
        missingEnvBody="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable server-side prediction reads in the website."
        errorTitle="Prediction query failed"
        emptyTitle="No predictions available"
        emptyBody="No latest prediction snapshot was found for the selected band."
      />
    );
  }

  const [nextShowState, specificShowState, missingSetlistShows] =
    await Promise.all([
      getNextShowDetails(predictionState.band, clock.todayIso),
      getShowDetailsByDate(
        predictionState.band,
        predictionState.snapshot.targetShowDate,
      ),
      getRecentMissingSetlistShows(
        predictionState.band,
        predictionState.snapshot.targetShowDate,
        clock,
      ),
    ]);
  const nextShow = nextShowState.status === "ready" ? nextShowState.show : null;
  const specificShow = specificShowState.status === "ready" ? specificShowState.show : null;

  const targetShow = nextShow?.showDate === predictionState.snapshot.targetShowDate
    ? nextShow
    : specificShow;

  const heroDate = predictionState.snapshot.targetShowDate;
  const pendingNextShow =
    nextShow && nextShow.showDate && nextShow.showDate !== heroDate
      ? {
          dateLabel: formatCompactDateLabel(nextShow.showDate),
          venueName: nextShow.venueName,
          locationLabel:
            buildLocationLabel([
              nextShow.city,
              nextShow.state ?? nextShow.country,
            ]) || null,
        }
      : null;
  const dateLabel = formatDateLabel(heroDate);
  const locationLabel = buildLocationLabel([
    targetShow?.city ?? null,
    targetShow?.state ?? targetShow?.country ?? null,
  ]);
  const isLiveShow = isShowTonight(heroDate);
  const displayState = getPredictionDisplayState(heroDate);
  const statusLabel = getPredictionStatusLabel(heroDate);
  const snapshotLabel = formatTimestampLabel(predictionState.snapshot.predictedAt);
  const searchSongs = predictionState.snapshot.predictions.map((row) => ({
    rank: row.rank,
    songName: row.songName,
    tier: row.tier,
    currentGap: row.currentGap,
    lastPlayed: row.lastPlayed,
  }));

  const shareText = formatTop10Text({
    bandName,
    dateLabel,
    locationLabel,
    venueName: targetShow?.venueName ?? "",
    predictions: predictionState.snapshot.predictions,
    shareUrl: `jambandnerd.com${bandPath(band, "predictions")}`,
  });

  return (
    <>
      {heroDate &&
        isLiveShow &&
        process.env.NEXT_PUBLIC_SUPABASE_URL &&
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY && (
        <LiveTracker
          band={predictionState.band}
          targetShowKey={predictionState.snapshot.targetShowKey}
          targetShowDate={heroDate}
        />
      )}

      <PredictionHero
        venueName={targetShow?.venueName ?? `${bandName} Show`}
        dateLabel={dateLabel}
        locationLabel={locationLabel}
        statusLabel={statusLabel}
        snapshotLabel={snapshotLabel}
        displayState={displayState}
        heroShowDate={heroDate}
        missingSetlistShows={missingSetlistShows}
        pendingNextShow={pendingNextShow}
      />
      <Suspense fallback={<AccuracyMetricsFallback />}>
        <PredictionAccuracyMetrics band={band} todayIso={clock.todayIso} />
      </Suspense>

      <section className="px-1">
        <div className="px-3 py-2 sm:px-4 md:px-5">
          <div className="text-center md:text-left">
            <p className="font-label text-[10px] uppercase tracking-[0.24em] text-primary">
              Full ranking
            </p>
            <h2 className="mt-3 font-headline text-3xl font-bold uppercase tracking-[-0.04em] text-on-surface">
              Song board
            </h2>
          </div>
          <div className="mt-5 flex items-center gap-3 md:gap-4">
            <div className="flex flex-1">
              <SongSearch songs={searchSongs} />
            </div>
            <div className="shrink-0">
              <SharePredictionsButton text={shareText} />
            </div>
          </div>
          <div className="mt-6">
            <SongBoard rows={predictionState.snapshot.predictions} />
          </div>
        </div>
      </section>
    </>
  );
}
