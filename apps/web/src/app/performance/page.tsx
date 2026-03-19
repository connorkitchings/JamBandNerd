import { AccuracyTable } from "@/components/accuracy-table";
import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { SectionCard } from "@/components/section-card";
import { BAND_CONFIG, MODEL_CONFIG } from "@/lib/config";
import { getRecentAccuracy } from "@/lib/data";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
  }>;
};

function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value !== null);
  if (filtered.length === 0) {
    return "—";
  }
  return `${((filtered.reduce((sum, value) => sum + value, 0) / filtered.length) * 100).toFixed(1)}%`;
}

export default async function PerformancePage({ searchParams }: Props) {
  const params = await searchParams;
  const state = await getRecentAccuracy(params.band, params.model, 20);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_KEY to enable the performance route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Performance query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No accuracy rows available"
        body="The route is present, but no accuracy rows were returned from the unified accuracy table."
      />
    );
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Historical Performance" eyebrow="Parity View">
        <FilterLinks pathname="/performance" band={state.band} model={state.model} />
      </SectionCard>

      <section className="grid gap-4 md:grid-cols-3">
        <SectionCard title={average(state.rows.map((row) => row.k10Recall))} eyebrow="Avg Top 10">
          <p className="text-sm text-on-surface-variant">{BAND_CONFIG[state.band].displayName}</p>
        </SectionCard>
        <SectionCard title={average(state.rows.map((row) => row.k25Recall))} eyebrow="Avg Top 25">
          <p className="text-sm text-on-surface-variant">{MODEL_CONFIG[state.model].displayName}</p>
        </SectionCard>
        <SectionCard title={average(state.rows.map((row) => row.k50Recall))} eyebrow="Avg Top 50">
          <p className="text-sm text-on-surface-variant">Last {state.rows.length} shows</p>
        </SectionCard>
      </section>

      <SectionCard title="Recent Accuracy Rows" eyebrow="Server Table">
        <AccuracyTable rows={state.rows} />
      </SectionCard>
    </div>
  );
}
