import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { PredictionTable } from "@/components/prediction-table";
import { SectionCard } from "@/components/section-card";
import { BAND_CONFIG, MODEL_CONFIG } from "@/lib/config";
import { getLatestPredictions } from "@/lib/data";

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
        body="The website route is wired up, but no latest prediction row was found for the selected band/model."
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Latest Predictions" eyebrow="Server-Side Supabase">
        <FilterLinks pathname="/predictions" band={state.band} model={state.model} />
      </SectionCard>

      <section className="rounded-xl border border-outline-variant/30 bg-gradient-to-br from-surface to-surface-container p-8">
        <p className="text-sm text-on-surface-variant">
          {BAND_CONFIG[state.band].displayName} · {MODEL_CONFIG[state.model].displayName}
        </p>
        <h1 className="mt-2 font-headline text-3xl font-semibold text-on-surface">
          Reference date {state.snapshot.referenceDate ?? "unknown"}
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
          This is the first website-native prediction route. It already reads the unified prediction
          tables on the server and renders the top songs without going through the legacy Streamlit
          runtime.
        </p>
        <div className="mt-5 flex flex-wrap gap-3 font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
          <span>Predicted at {state.snapshot.predictedAt ?? "unknown"}</span>
          <span>Model version {state.snapshot.modelVersion ?? "unknown"}</span>
        </div>
      </section>

      <SectionCard title="Top 10 Songs" eyebrow="Route Shell">
        <PredictionTable rows={state.snapshot.predictions} mode={state.model} />
      </SectionCard>
    </div>
  );
}
