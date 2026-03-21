import type { Metadata } from "next";
import { AccuracyTable } from "@/components/accuracy-table";
import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { RecallChart } from "@/components/recall-chart";
import { SectionCard } from "@/components/section-card";
import { MODEL_CONFIG, normalizeBand, normalizeModel } from "@/lib/config";
import { type AccuracyRow, getBands, getRecentAccuracy, bandEntryBySlug } from "@/lib/data";
import { formatCompactDateLabel, formatPercent } from "@/lib/format";

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
  const bandSlug = normalizeBand(params.band);
  const bandEntry = bandEntryBySlug(bands, bandSlug);
  const model = normalizeModel(params.model);
  const bandName = bandEntry?.displayName ?? bandSlug;
  const modelName = MODEL_CONFIG[model].displayName;

  return {
    title: `${bandName} Performance Ledger | JamBandNerd`,
    description: `Track historical prediction accuracy for ${bandName} using the ${modelName} model.`,
  };
}

function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value !== null);
  if (filtered.length === 0) {
    return null;
  }
  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}

function getBestRecallRow(rows: AccuracyRow[]) {
  return rows.reduce<AccuracyRow | null>((best, row) => {
    if (!best) {
      return row;
    }
    return (row.k10Recall ?? -1) > (best.k10Recall ?? -1) ? row : best;
  }, null);
}

export default async function PerformancePage({ searchParams }: Props) {
  const params = await searchParams;
  const [bandsResult, state] = await Promise.all([
    getBands(),
    getRecentAccuracy(params.band, params.model, 20),
  ]);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the performance route."
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
        body="No accuracy rows were returned from the unified accuracy table."
      />
    );
  }

  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const normalizedBand = normalizeBand(params.band);
  if (!bands.some((b) => b.slug === normalizedBand)) {
    return (
      <DataState
        title="Band not found"
        body={`No active band found for slug "${normalizedBand}". Select a supported band from the navigation.`}
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;

  const top10Average = average(state.rows.map((row) => row.k10Recall));
  const top25Average = average(state.rows.map((row) => row.k25Recall));
  const top50Average = average(state.rows.map((row) => row.k50Recall));
  const latestRow = state.rows[0] ?? null;
  const recentWindow = average(state.rows.slice(0, 5).map((row) => row.k10Recall));
  const priorWindow = average(state.rows.slice(5, 10).map((row) => row.k10Recall));
  const trendDelta =
    recentWindow !== null && priorWindow !== null ? recentWindow - priorWindow : null;
  const bestRow = getBestRecallRow(state.rows);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Historical Performance" eyebrow="Model Recall">
        <FilterLinks pathname="/performance" band={state.band} model={state.model} bands={bands} />
      </SectionCard>

      <section className="rounded-xl border border-outline-variant/30 bg-surface-container p-8 md:p-10">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
          <div>
            <p className="font-label text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
              Rolling accuracy
            </p>
            <h1 className="mt-3 font-headline text-4xl font-semibold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
              {bandName} performance ledger
            </h1>
            <p className="mt-3 font-headline text-base uppercase tracking-[0.08em] text-primary">
              {MODEL_CONFIG[state.model].displayName} • last {state.rows.length} scored shows
            </p>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-on-surface-variant">
              Track how often the current model landed songs inside the Top 10, Top 25, and Top 50
              windows. The goal here is fast read quality, not exhaustive backtest detail.
            </p>
          </div>
          <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
              Latest scored show
            </p>
            <p className="mt-3 font-headline text-2xl font-semibold text-on-surface">
              {formatCompactDateLabel(latestRow?.showDate ?? null)}
            </p>
            <p className="mt-2 text-sm text-on-surface-variant">
              {latestRow?.venueName ?? "Venue unavailable"}
            </p>
            <p className="mt-4 text-sm text-primary">
              Top 10 recall {formatPercent(latestRow?.k10Recall ?? null)}
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <SectionCard title={formatPercent(top10Average)} eyebrow="Avg Top 10">
          <p className="text-sm leading-6 text-on-surface-variant">
            Quick-hit prediction quality for the highest-confidence slice.
          </p>
        </SectionCard>
        <SectionCard title={formatPercent(top25Average)} eyebrow="Avg Top 25">
          <p className="text-sm leading-6 text-on-surface-variant">
            Broader board coverage across the mid-ranked prediction set.
          </p>
        </SectionCard>
        <SectionCard title={formatPercent(top50Average)} eyebrow="Avg Top 50">
          <p className="text-sm leading-6 text-on-surface-variant">
            Long-tail hit rate across the full recommendation window.
          </p>
        </SectionCard>
      </section>

      <SectionCard title="Recall Timeline" eyebrow="Top-10 accuracy over time">
        <RecallChart rows={state.rows} />
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <SectionCard title="Performance Read" eyebrow="Trend">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Recent window
              </p>
              <p className="mt-2 font-headline text-2xl font-semibold text-on-surface">
                {formatPercent(recentWindow)}
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">Last five scored shows</p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Prior window
              </p>
              <p className="mt-2 font-headline text-2xl font-semibold text-on-surface">
                {formatPercent(priorWindow)}
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">Previous five scored shows</p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Delta
              </p>
              <p className="mt-2 font-headline text-2xl font-semibold text-primary">
                {trendDelta === null
                  ? "—"
                  : `${trendDelta >= 0 ? "+" : ""}${(trendDelta * 100).toFixed(1)} pts`}
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">
                {trendDelta === null
                  ? "Need at least 10 rows for a trend comparison."
                  : trendDelta >= 0
                    ? "Recent recall is improving."
                    : "Recent recall has slipped versus the prior window."}
              </p>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Best Night" eyebrow="Peak recall">
          <div className="space-y-3">
            <p className="font-headline text-2xl font-semibold text-on-surface">
              {formatCompactDateLabel(bestRow?.showDate ?? null)}
            </p>
            <p className="text-sm text-on-surface-variant">
              {bestRow?.venueName ?? "Venue unavailable"}
            </p>
            <p className="text-sm text-primary">
              Top 10 recall {formatPercent(bestRow?.k10Recall ?? null)}
            </p>
            <p className="text-sm text-on-surface-variant">
              Use this as the fast benchmark for the current model and band pair.
            </p>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Recent Accuracy Rows" eyebrow="Per-show ledger">
        <AccuracyTable rows={state.rows} />
      </SectionCard>
    </div>
  );
}
