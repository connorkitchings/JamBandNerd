import type { Metadata } from "next";
import Link from "next/link";

import { DashboardAnalysis } from "@/components/dashboard-analysis";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { PredictionHero } from "@/components/prediction-hero";
import { SongBoard } from "@/components/song-board";
import { SongSearch } from "@/components/song-search";
import { MODEL_CONFIG, normalizeModel } from "@/lib/config";
import {
  resolveBandSelection,
  getBands,
  getLatestPredictions,
  getRecentAccuracy,
  getShowDetailsByDate,
  calculateModelAgreement,
  bandEntryBySlug,
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

export default async function HomePage({ searchParams }: Props) {
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
  const secondaryModelSlug = normalizeModel(params.model) === "ckplus" ? "notebook" : "ckplus";

  const [predictionState, secondaryPredictionState, accuracyState] = await Promise.all([
    getLatestPredictions(selectedBand, params.model),
    getLatestPredictions(selectedBand, secondaryModelSlug),
    getRecentAccuracy(selectedBand, params.model, 10),
  ]);

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

  const bandEntry = bandEntryBySlug(bands, predictionState.band) ?? { slug: predictionState.band, displayName: predictionState.band, showsTable: "", idColumn: "" };
  const bandName = bandEntry.displayName;

  const showState = await getShowDetailsByDate(
    predictionState.band,
    predictionState.snapshot.referenceDate,
  );

  const showDetails = showState.status === "ready" ? showState.show : null;
  const referenceDate = showDetails?.showDate ?? predictionState.snapshot.referenceDate;
  const dateLabel = formatDateLabel(referenceDate);
  const locationLabel = buildLocationLabel([
    showDetails?.city ?? null,
    showDetails?.state ?? showDetails?.country ?? null,
  ]);
  const today = new Date().toISOString().slice(0, 10);
  const statusLabel =
    referenceDate && referenceDate >= today ? "Pre-Show" : "Latest Snapshot";
  const snapshotLabel = formatTimestampLabel(predictionState.snapshot.predictedAt);
  const accuracyRows = accuracyState.status === "ready" ? accuracyState.rows : [];

  const searchSongs = predictionState.snapshot.predictions.map((row) => ({
    rank: row.rank,
    songName: row.songName,
    tier: row.tier,
    currentGap: row.currentGap,
    lastPlayed: row.lastPlayed,
  }));

  const agreementScore =
    secondaryPredictionState.status === "ready"
      ? calculateModelAgreement(
          predictionState.snapshot.predictions,
          secondaryPredictionState.snapshot.predictions,
        )
      : null;

  return (
    <div className="w-full pb-6 lg:pl-64">
      <DashboardSideNav band={predictionState.band} model={predictionState.model} bands={bands} />

      <PredictionHero
        venueName={
          showDetails?.venueName ?? `${bandName} Snapshot`
        }
        dateLabel={dateLabel}
        locationLabel={locationLabel}
        statusLabel={statusLabel}
        modelLabel={MODEL_CONFIG[predictionState.model].displayName}
        bandLabel={bandName}
        snapshotLabel={snapshotLabel}
        totalSongs={predictionState.snapshot.predictions.length}
        accuracyRows={accuracyRows}
        predictions={predictionState.snapshot.predictions}
        agreementScore={agreementScore}
      />

      <section>
        <div className="mb-6 flex items-end justify-between border-b border-outline-variant/20 pb-4">
          <div>
            <h2 className="font-headline text-2xl font-bold uppercase tracking-tight text-on-surface">
              Song Board
            </h2>
            <p className="text-xs text-on-surface-variant">
              All ranked predictions for {bandName} using{" "}
              {MODEL_CONFIG[predictionState.model].displayName}. Tiers reflect relative likelihood, not guarantees.
            </p>
          </div>
          <div className="hidden gap-2 sm:flex">
            <Link
              href={`/explorer?band=${predictionState.band}&model=${predictionState.model}`}
              className="rounded-lg bg-surface-container-high px-3 py-2 font-label text-[10px] uppercase tracking-[0.16rem] text-primary transition hover:bg-surface-container-highest"
            >
              Explorer
            </Link>
            <Link
              href={`/compare?band=${predictionState.band}`}
              className="rounded-lg bg-surface-container px-3 py-2 font-label text-[10px] uppercase tracking-[0.16rem] text-outline transition hover:text-on-surface"
            >
              Compare
            </Link>
          </div>
        </div>

        <div className="mb-6">
          <SongSearch songs={searchSongs} />
        </div>

        <SongBoard rows={predictionState.snapshot.predictions} />
      </section>

      <DashboardAnalysis
        rows={accuracyRows}
        predictions={predictionState.snapshot.predictions}
        bandLabel={bandName}
        modelLabel={MODEL_CONFIG[predictionState.model].displayName}
      />

      <footer className="mt-16 border-t border-white/10 py-10">
        <div className="flex flex-col gap-4 text-xs text-on-surface/40 md:flex-row md:items-center md:justify-between">
          <p>© 2026 JamBandNerd Archivist Labs</p>
          <div className="flex gap-6">
            <a className="underline decoration-dotted transition hover:text-primary" href="https://github.com/" rel="noopener noreferrer" target="_blank">
              GitHub
            </a>
            <Link className="underline decoration-dotted transition hover:text-primary" href="/about">
              About
            </Link>
            <Link className="underline decoration-dotted transition hover:text-primary" href={`/performance?band=${predictionState.band}&model=${predictionState.model}`}>
              Performance
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
