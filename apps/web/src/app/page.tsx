import Link from "next/link";

import { DashboardAnalysis } from "@/components/dashboard-analysis";
import { DashboardHero } from "@/components/dashboard-hero";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { PredictionTable } from "@/components/prediction-table";
import { BAND_CONFIG, MODEL_CONFIG } from "@/lib/config";
import { getLatestPredictions, getRecentAccuracy, getShowDetailsByDate } from "@/lib/data";
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

function getFallbackConfidence(predictionState: Awaited<ReturnType<typeof getLatestPredictions>>) {
  if (predictionState.status !== "ready") {
    return null;
  }

  const top = predictionState.snapshot.predictions[0];
  if (!top) {
    return null;
  }

  if (top.probability !== null) {
    return Math.round(Math.max(0, Math.min(1, top.probability)) * 100);
  }

  if (predictionState.model === "notebook") {
    return Math.min(99, Math.max(18, (top.playsPastYear ?? top.rank) * 6));
  }

  return Math.min(99, Math.max(18, Math.round((top.ckplusScore ?? top.gapRatio ?? top.rank) * 18)));
}

function getConfidenceLabel(value: number | null) {
  if (value === null) {
    return "Signal Pending";
  }

  if (value >= 90) {
    return "High Fidelity";
  }

  if (value >= 75) {
    return "Stable Read";
  }

  if (value >= 60) {
    return "Moderate Signal";
  }

  return "Volatile Read";
}

export default async function HomePage({ searchParams }: Props) {
  const params = await searchParams;
  const [predictionState, accuracyState] = await Promise.all([
    getLatestPredictions(params.band, params.model),
    getRecentAccuracy(params.band, params.model, 10),
  ]);

  if (predictionState.status === "missing_env") {
    return (
      <div className="mx-auto max-w-6xl">
        <DataState
          title="Supabase environment required"
          body="Set SUPABASE_URL and SUPABASE_KEY to enable server-side prediction reads in the website."
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
          body="The homepage is wired to the live prediction tables, but no latest snapshot was returned for the selected band and model."
        />
      </div>
    );
  }

  const showState = await getShowDetailsByDate(
    predictionState.band,
    predictionState.snapshot.referenceDate,
  );

  const showDetails = showState.status === "ready" ? showState.show : null;
  const averageRecall =
    accuracyState.status === "ready" && accuracyState.rows.length > 0
      ? Math.round(
          (accuracyState.rows.reduce((sum, row) => sum + (row.k10Recall ?? 0), 0) /
            accuracyState.rows.length) *
            100,
        )
      : getFallbackConfidence(predictionState);

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
  const topKLabel = `Top ${Math.min(10, predictionState.snapshot.predictions.length || 10)}`;

  return (
    <div className="w-full pb-6 lg:pl-64">
      <DashboardSideNav band={predictionState.band} model={predictionState.model} />

      <DashboardHero
        venueName={
          showDetails?.venueName ?? `${BAND_CONFIG[predictionState.band].displayName} Snapshot`
        }
        dateLabel={dateLabel}
        locationLabel={locationLabel}
        statusLabel={statusLabel}
        modelLabel={MODEL_CONFIG[predictionState.model].displayName}
        topKLabel={topKLabel}
        snapshotLabel={snapshotLabel}
        confidencePercent={averageRecall}
        confidenceLabel={getConfidenceLabel(averageRecall)}
      />

      <section>
        <div className="mb-8 flex items-end justify-between border-b border-outline-variant/20 pb-4">
          <div>
            <h2 className="font-headline text-2xl font-bold uppercase tracking-tight text-on-surface">
              The Expected
            </h2>
            <p className="text-xs text-on-surface-variant">
              Top current predictions for {BAND_CONFIG[predictionState.band].displayName} using{" "}
              {MODEL_CONFIG[predictionState.model].displayName}.
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

        <PredictionTable rows={predictionState.snapshot.predictions} mode={predictionState.model} />
      </section>

      <DashboardAnalysis
        rows={accuracyState.status === "ready" ? accuracyState.rows : []}
        predictions={predictionState.snapshot.predictions}
        bandLabel={BAND_CONFIG[predictionState.band].displayName}
        modelLabel={MODEL_CONFIG[predictionState.model].displayName}
      />

      <footer className="mt-16 border-t border-white/10 py-10">
        <div className="flex flex-col gap-4 text-xs text-on-surface/40 md:flex-row md:items-center md:justify-between">
          <p>© 2026 JamBandNerd Archivist Labs</p>
          <div className="flex gap-6">
            <a className="underline decoration-dotted transition hover:text-primary" href="https://github.com/" rel="noreferrer" target="_blank">
              GitHub
            </a>
            <Link className="underline decoration-dotted transition hover:text-primary" href="/about">
              About
            </Link>
            <Link className="underline decoration-dotted transition hover:text-primary" href="/performance?band=goose&model=notebook">
              Performance
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
