import type { Metadata } from "next";

import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { LiveTracker } from "@/components/live-tracker";
import { PredictionHero } from "@/components/prediction-hero";
import { SongBoard } from "@/components/song-board";
import { SongSearch } from "@/components/song-search";
import { MODEL_CONFIG, normalizeModel } from "@/lib/config";
import {
  bandEntryBySlug,
  getBands,
  getLatestPredictions,
  getNextShowDetails,
  resolveBandSelection,
} from "@/lib/data";
import {
  buildLocationLabel,
  formatDateLabel,
  formatTimestampLabel,
} from "@/lib/format";

export const dynamic = "force-dynamic";

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

  return {
    title: `${bandName} Setlist Predictions | JamBandNerd`,
    description: `Latest ${modelName} model setlist predictions for ${bandName}, ranked by likelihood tier.`,
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

  const nextShowState = await getNextShowDetails(predictionState.band);
  const nextShow = nextShowState.status === "ready" ? nextShowState.show : null;
  const heroDate = nextShow?.showDate ?? predictionState.snapshot.referenceDate;
  const dateLabel = formatDateLabel(heroDate);
  const locationLabel = buildLocationLabel([
    nextShow?.city ?? null,
    nextShow?.state ?? nextShow?.country ?? null,
  ]);
  const today = new Date().toISOString().slice(0, 10);
  const statusLabel =
    heroDate === today
      ? "LIVE"
      : nextShow?.showDate
        ? "Next Show"
        : "Prediction Outlook";
  const snapshotLabel = formatTimestampLabel(predictionState.snapshot.predictedAt);

  const searchSongs = predictionState.snapshot.predictions.map((row) => ({
    rank: row.rank,
    songName: row.songName,
    tier: row.tier,
    currentGap: row.currentGap,
    lastPlayed: row.lastPlayed,
  }));

  return (
    <div className="w-full max-w-6xl mx-auto">
      <DashboardSideNav
        band={predictionState.band}
        model={predictionState.model}
        bands={bands}
      />

      {process.env.SUPABASE_URL && process.env.SUPABASE_ANON_KEY && (
        <LiveTracker
          supabaseUrl={process.env.SUPABASE_URL}
          supabaseAnonKey={process.env.SUPABASE_ANON_KEY}
        />
      )}

      <PredictionHero
        venueName={nextShow?.venueName ?? `${bandName} Next Show`}
        dateLabel={dateLabel}
        locationLabel={locationLabel}
        statusLabel={statusLabel}
        modelSlug={predictionState.model}
        snapshotLabel={snapshotLabel}
        totalSongs={predictionState.snapshot.predictions.length}
        predictions={predictionState.snapshot.predictions}
      />

      <section>
        <div className="mb-6 border-b border-outline-variant/20 pb-4">
          <div>
            <h2 className="font-headline text-2xl font-bold uppercase tracking-tight text-on-surface">
              Song Board
            </h2>
            <p className="text-xs text-on-surface-variant">
              All ranked predictions for {bandName} using{" "}
              {MODEL_CONFIG[predictionState.model].displayName}. Tiers reflect relative
              likelihood, not guarantees.
            </p>
          </div>
        </div>

        <div className="mb-6">
          <SongSearch songs={searchSongs} />
        </div>

        <SongBoard rows={predictionState.snapshot.predictions} modelSlug={predictionState.model} />
      </section>
    </div>
  );
}
