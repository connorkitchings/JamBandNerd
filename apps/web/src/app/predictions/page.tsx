import type { Metadata } from "next";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { LiveTracker } from "@/components/live-tracker";
import { PredictionHero } from "@/components/prediction-hero";
import { SharePredictionsButton } from "@/components/share-predictions-button";
import { SongBoard } from "@/components/song-board";
import { SongSearch } from "@/components/song-search";
import { MODEL_CONFIG, normalizeModel } from "@/lib/config";
import {
  bandEntryBySlug,
  getBands,
  getLatestPredictions,
  getNextShowDetails,
  getRecentAccuracy,
  resolveBandSelection,
} from "@/lib/data";
import {
  buildLocationLabel,
  formatDateLabel,
  formatPercent,
  formatTimestampLabel,
} from "@/lib/format";
import { formatTop10Text } from "@/lib/format-predictions-text";

export const dynamic = "force-dynamic";

function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value !== null);
  if (filtered.length === 0) {
    return null;
  }

  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
  }>;
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const model = normalizeModel(params.model);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;
  const modelName = MODEL_CONFIG[model].displayName;

  const title = `${bandName} Setlist Predictions | JamBandNerd`;
  const description = `Latest ${modelName} model setlist predictions for ${bandName}, ranked by likelihood tier.`;
  const url = `https://jambandnerd.com/predictions?band=${params.band ?? "goose"}&model=${model}`;

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
  const predictionState = await getLatestPredictions(selectedBand, params.model);

  if (predictionState.status === "missing_env") {
    return (
      <div className="mx-auto max-w-6xl">
        <DataState
          title="Supabase environment required"
          body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable server-side prediction reads in the website."
        />
      </div>
    );
  }

  if (predictionState.status === "error") {
    return (
      <div className="mx-auto max-w-6xl">
        <DataState title="Prediction query failed" body={predictionState.message} />
      </div>
    );
  }

  if (predictionState.status === "empty") {
    return (
      <div className="mx-auto max-w-6xl">
        <DataState
          title="No predictions available"
          body="No latest prediction snapshot was found for the selected band and model."
        />
      </div>
    );
  }

  const bandEntry = bandEntryBySlug(bands, predictionState.band) ?? {
    slug: predictionState.band,
    displayName: predictionState.band,
    showsTable: "",
    idColumn: "",
  };
  const bandName = bandEntry.displayName;

  const [nextShowState, accuracyState] = await Promise.all([
    getNextShowDetails(predictionState.band),
    getRecentAccuracy(predictionState.band, predictionState.model, 50),
  ]);
  const nextShow = nextShowState.status === "ready" ? nextShowState.show : null;
  const heroDate = nextShow?.showDate ?? predictionState.snapshot.referenceDate;
  const dateLabel = formatDateLabel(heroDate);
  const locationLabel = buildLocationLabel([
    nextShow?.city ?? null,
    nextShow?.state ?? nextShow?.country ?? null,
  ]);
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });
  const isLiveShow = heroDate === today;
  const statusLabel =
    isLiveShow
      ? "Tonight!"
      : nextShow?.showDate
        ? "Next Show"
        : "Prediction Outlook";
  const snapshotLabel = formatTimestampLabel(predictionState.snapshot.predictedAt);
  const accuracyRows = accuracyState.status === "ready" ? accuracyState.rows : [];
  const accuracyWindow = accuracyRows.length || 50;
  const precisionCards = [
    {
      title: "Top 10 Accuracy",
      value: formatPercent(average(accuracyRows.map((row) => row.k10Recall))),
      description: `last ${accuracyWindow} shows`,
    },
    {
      title: "Top 25 Accuracy",
      value: formatPercent(average(accuracyRows.map((row) => row.k25Recall))),
      description: `last ${accuracyWindow} shows`,
    },
    {
      title: "Top 50 Accuracy",
      value: formatPercent(average(accuracyRows.map((row) => row.k50Recall))),
      description: `last ${accuracyWindow} shows`,
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
    venueName: nextShow?.venueName ?? "",
    predictions: predictionState.snapshot.predictions,
    modelDisplayName: MODEL_CONFIG[predictionState.model].displayName,
    shareUrl: `jambandnerd.com/predictions?band=${predictionState.band}&model=${predictionState.model}`,
  });

  return (
    <div className="mx-auto w-full max-w-6xl">
      <DashboardSideNav
        band={predictionState.band}
        model={predictionState.model}
        bands={bands}
      />

      {isLiveShow && process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY && (
        <LiveTracker
          band={predictionState.band}
          model={predictionState.model}
          referenceDate={heroDate}
          supabaseUrl={process.env.SUPABASE_URL}
          supabaseAnonKey={process.env.SUPABASE_ANON_KEY}
        />
      )}

      <PredictionHero
        venueName={nextShow?.venueName ?? `${bandName} Next Show`}
        dateLabel={dateLabel}
        locationLabel={locationLabel}
        statusLabel={statusLabel}
        snapshotLabel={snapshotLabel}
        predictions={predictionState.snapshot.predictions}
        precisionCards={precisionCards}
        metricCaption="Accuracy is measured as the share of the actual setlist included in each Top-X group."
      />

      <section>
        <div className="editorial-panel px-4 py-5 sm:px-6 sm:py-6 md:px-7">
          <div className="relative flex items-start justify-between gap-4">
            <div>
              <p className="font-label text-[10px] uppercase tracking-[0.24em] text-primary">
                Full ranking
              </p>
              <h2 className="mt-3 font-headline text-3xl font-bold uppercase tracking-[-0.04em] text-on-surface">
                Song board
              </h2>
              <p className="mt-3 text-sm leading-7 text-on-surface-variant">
                All ranked predictions for {bandName} using{" "}
                {MODEL_CONFIG[predictionState.model].displayName}. Use the search first, then scan
                by tier to understand how the board is clustering tonight.
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
            <SongBoard rows={predictionState.snapshot.predictions} modelSlug={predictionState.model} />
          </div>
        </div>
      </section>
    </div>
  );
}
