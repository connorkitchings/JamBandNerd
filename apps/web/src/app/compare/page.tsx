import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { PredictionTable } from "@/components/prediction-table";
import { SectionCard } from "@/components/section-card";
import { BAND_CONFIG } from "@/lib/config";
import { getLatestPredictions } from "@/lib/data";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
  }>;
};

export default async function ComparePage({ searchParams }: Props) {
  const params = await searchParams;
  const [notebook, ckplus] = await Promise.all([
    getLatestPredictions(params.band, "notebook"),
    getLatestPredictions(params.band, "ckplus"),
  ]);

  if (notebook.status === "missing_env" || ckplus.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_KEY to enable the comparison route."
      />
    );
  }

  if (notebook.status !== "ready" || ckplus.status !== "ready") {
    return (
      <DataState
        title="Comparison data unavailable"
        body="The compare route is scaffolded, but both model snapshots were not available."
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Model Compare" eyebrow="Parity View">
        <FilterLinks pathname="/compare" band={notebook.band} />
      </SectionCard>

      <section className="rounded-xl border border-outline-variant/30 bg-surface-container p-8">
        <h1 className="font-headline text-3xl font-semibold text-on-surface">
          {BAND_CONFIG[notebook.band].displayName} model comparison
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
          This page already exercises the website’s intended model-comparison pattern by fetching
          both latest snapshots in parallel on the server.
        </p>
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Notebook" eyebrow={notebook.snapshot.referenceDate ?? "No date"}>
          <PredictionTable rows={notebook.snapshot.predictions} mode="notebook" />
        </SectionCard>
        <SectionCard title="CK+" eyebrow={ckplus.snapshot.referenceDate ?? "No date"}>
          <PredictionTable rows={ckplus.snapshot.predictions} mode="ckplus" />
        </SectionCard>
      </div>
    </div>
  );
}
