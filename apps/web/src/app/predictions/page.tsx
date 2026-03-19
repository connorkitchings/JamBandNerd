import Link from "next/link";

import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { PredictionTable } from "@/components/prediction-table";
import { SectionCard } from "@/components/section-card";
import { BAND_CONFIG, MODEL_CONFIG } from "@/lib/config";
import { getLatestPredictions } from "@/lib/data";
import { formatDateLabel, formatTimestampLabel } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
  }>;
};

export default async function PredictionsPage({ searchParams }: Props) {
  const params = await searchParams;
  const state = await getLatestPredictions(params.band, params.model);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_KEY to enable server-side prediction reads in the website."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Prediction query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No predictions available"
        body="No latest prediction snapshot was found for the selected band and model."
      />
    );
  }

  const topSong = state.snapshot.predictions[0]?.songName ?? "No ranked songs";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Latest Predictions" eyebrow="Live Board">
        <FilterLinks pathname="/predictions" band={state.band} model={state.model} />
      </SectionCard>

      <section className="rounded-xl border border-outline-variant/30 bg-gradient-to-br from-surface to-surface-container p-8 md:p-10">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.8fr)]">
          <div>
            <p className="font-label text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
              Current prediction board
            </p>
            <h1 className="mt-3 font-headline text-4xl font-semibold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
              {BAND_CONFIG[state.band].displayName} · {MODEL_CONFIG[state.model].displayName}
            </h1>
            <p className="mt-3 font-headline text-base uppercase tracking-[0.08em] text-primary">
              Reference date {formatDateLabel(state.snapshot.referenceDate)}
            </p>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-on-surface-variant">
              This route is the direct latest-snapshot board for the selected band and model. It is
              the simplest path for reading the current ranking without the homepage hero context.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href={`/?band=${state.band}&model=${state.model}`}
                className="rounded-lg bg-surface-container-high px-3 py-2 font-label text-[10px] uppercase tracking-[0.16rem] text-primary transition hover:bg-surface-container-highest"
              >
                Dashboard
              </Link>
              <Link
                href={`/explorer?band=${state.band}&model=${state.model}`}
                className="rounded-lg bg-surface-container px-3 py-2 font-label text-[10px] uppercase tracking-[0.16rem] text-outline transition hover:text-on-surface"
              >
                Explorer
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Top call
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-on-surface">
                {topSong}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Snapshot metadata
              </p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                Predicted at {formatTimestampLabel(state.snapshot.predictedAt)}
              </p>
              <p className="text-sm leading-6 text-on-surface-variant">
                Model version {state.snapshot.modelVersion ?? "Unknown"}
              </p>
            </div>
          </div>
        </div>
      </section>

      <SectionCard title="Top 10 Songs" eyebrow="Current ranking">
        <PredictionTable rows={state.snapshot.predictions} mode={state.model} />
      </SectionCard>
    </div>
  );
}
