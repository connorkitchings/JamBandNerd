import type { Metadata } from "next";
import Link from "next/link";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataGate } from "@/components/data-gate";
import { DataState } from "@/components/data-state";
import { LiveTracker } from "@/components/live-tracker";
import { PredictionHero, PredictionHeroMetrics } from "@/components/prediction-hero";
import { SharePredictionsButton } from "@/components/share-predictions-button";
import { SongBoard } from "@/components/song-board";
import { SongSearch } from "@/components/song-search";
import {
  bandEntryBySlug,
  getBands,
  getLatestPredictions,
  getNextShowDetails,
  getShowDetailsByDate,
  getRecentAccuracy,
  resolveBandSelection,
} from "@/lib/data";
import {
  average,
  buildLocationLabel,
  formatDateLabel,
  formatAvgHits,
  formatPercent,
  formatTimestampLabel,
} from "@/lib/format";
import { formatTop10Text } from "@/lib/format-predictions-text";
import {
  getPredictionDisplayState,
  getPredictionStatusLabel,
  isShowTonight,
} from "@/lib/show-status";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
  }>;
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;

  const title = `${bandName} Setlist Predictions | JamBandNerd`;
  const description = `Latest setlist predictions for ${bandName}, ranked by likelihood tier.`;
  const url = `https://jambandnerd.com/predictions?band=${params.band ?? "goose"}`;

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

export default async function PredictionsPage({ searchParams }: Props) {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  if (bandsResult.status === "ready" && bandSelection.isInvalid) {
    return (
      <div className="mx-auto max-w-6xl">
        <DataState
          title="Band not found"
          body={`No active band found for slug "${bandSelection.requestedSlug}". Select a supported band from the navigation.`}
        />
      </div>
    );
  }

  const selectedBand =
    bandsResult.status === "ready" ? bandSelection.bandEntry?.slug : params.band;
  const predictionState = await getLatestPredictions(selectedBand);

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

  const bandEntry = bandEntryBySlug(bands, predictionState.band) ?? {
    slug: predictionState.band,
    displayName: predictionState.band,
    showsTable: "",
    idColumn: "",
  };
  const bandName = bandEntry.displayName;

  const [nextShowState, specificShowState, accuracyState] = await Promise.all([
    getNextShowDetails(predictionState.band),
    getShowDetailsByDate(predictionState.band, predictionState.snapshot.targetShowDate),
    getRecentAccuracy(predictionState.band, 50),
  ]);
  const nextShow = nextShowState.status === "ready" ? nextShowState.show : null;
  const specificShow = specificShowState.status === "ready" ? specificShowState.show : null;

  const targetShow = nextShow?.showDate === predictionState.snapshot.targetShowDate
    ? nextShow
    : specificShow;

  const heroDate = predictionState.snapshot.targetShowDate;
  const dateLabel = formatDateLabel(heroDate);
  const locationLabel = buildLocationLabel([
    targetShow?.city ?? null,
    targetShow?.state ?? targetShow?.country ?? null,
  ]);
  const isLiveShow = isShowTonight(heroDate);
  const displayState = getPredictionDisplayState(heroDate);
  const statusLabel = getPredictionStatusLabel(heroDate);
  const boardStateCopy =
    displayState === "tonight"
      ? "by tier to understand how the board is clustering tonight."
      : displayState === "next"
        ? "by tier to understand how the next-show board is shaping up."
        : "by tier to review what the model expected for that show.";
  const snapshotLabel = formatTimestampLabel(predictionState.snapshot.predictedAt);
  const accuracyRows = accuracyState.status === "ready" ? accuracyState.rows : [];
  const performanceWindowLabel =
    accuracyRows.length > 0
      ? `most recent ${accuracyRows.length} shows`
      : "no scored shows yet";
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
    shareUrl: `jambandnerd.com/predictions?band=${predictionState.band}`,
  });

  return (
    <div className="mx-auto w-full max-w-6xl">
      <DashboardSideNav
        band={predictionState.band}
        bands={bands}
      />

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

      {displayState === "previous" && (
        <div className="mb-5 rounded-lg border border-outline-variant/30 bg-surface-container-low px-4 py-3 text-sm leading-6 text-on-surface-variant">
          This board is for the previous known target show. It remains visible
          until the next upcoming show prediction is available.{" "}
          <Link
            href={`/last-show?band=${predictionState.band}`}
            className="font-semibold text-primary underline-offset-4 hover:underline"
          >
            View the latest completed show
          </Link>
          .
        </div>
      )}

      <PredictionHero
        venueName={targetShow?.venueName ?? `${bandName} Show`}
        dateLabel={dateLabel}
        locationLabel={locationLabel}
        statusLabel={statusLabel}
        snapshotLabel={snapshotLabel}
      />
      <PredictionHeroMetrics
        performanceWindowLabel={performanceWindowLabel}
        precisionCards={precisionCards}
      />

      <section className="px-1">
        <div className="px-3 py-2 sm:px-4 md:px-5">
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <p className="font-label text-[10px] uppercase tracking-[0.24em] text-primary">
                Full ranking
              </p>
              <h2 className="mt-3 font-headline text-3xl font-bold uppercase tracking-[-0.04em] text-on-surface">
                Song board
              </h2>
              <p className="mt-3 text-sm leading-7 text-on-surface-variant">
                All ranked predictions for {bandName}. Use the search first, then scan
                {` ${boardStateCopy}`}
              </p>
            </div>
            <div className="shrink-0 pt-1">
              <SharePredictionsButton text={shareText} />
            </div>
          </div>
          <div className="mt-5">
            <SongSearch songs={searchSongs} />
          </div>
          <div className="mt-6">
            <SongBoard rows={predictionState.snapshot.predictions} />
          </div>
        </div>
      </section>
    </div>
  );
}
