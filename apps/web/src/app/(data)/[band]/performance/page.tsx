import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { AccuracyTable } from "@/components/accuracy-table";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataGate } from "@/components/data-gate";
import { ExpandablePanel } from "@/components/expandable-panel";
import { MetricCard } from "@/components/metric-card";
import { PageHero } from "@/components/page-hero";
import { PageSkeleton } from "@/components/page-skeleton";
import { PerformanceChartPanel } from "@/components/performance-chart-panel";
import { SectionCard } from "@/components/section-card";
import { getRecentAccuracy, resolveBandPage } from "@/lib/data";
import { getEasternTodayIso } from "@/lib/show-status";
import { average, formatAvgHits, formatMMDDYYYY, formatHits, formatPercent } from "@/lib/format";

type Props = {
  params: Promise<{ band: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { bandEntry } = await resolveBandPage((await params).band);
  const bandName = bandEntry.displayName;

  return {
    title: `${bandName} Performance Ledger | JamBandNerd`,
    description: `Track historical prediction accuracy for ${bandName}.`,
  };
}

type PerformanceMetric = {
  label: string;
  coverage: number | null;
  avgHits: number | null;
  k: 10 | 25 | 50;
};

/** Coverage as the headline value, with the hit count as the hint. */
function CoverageMetricCard({
  metric,
  hitsPrefix = "Avg.",
  tone,
}: {
  metric: PerformanceMetric;
  hitsPrefix?: "Avg." | "";
  tone?: "accent";
}) {
  const hits =
    hitsPrefix === ""
      ? formatHits(metric.avgHits, metric.k)
      : formatAvgHits(metric.avgHits, metric.k);
  return (
    <MetricCard
      label={`${metric.label} coverage`}
      value={formatPercent(metric.coverage)}
      hint={`${hitsPrefix ? `${hitsPrefix} ` : ""}${hits} of ${metric.k} picks played`}
      tone={tone}
    />
  );
}

export default async function PerformancePage({ params }: Props) {
  const { band, bandEntry, bands } = await resolveBandPage((await params).band);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav band={band} bands={bands} page="performance" />
      <Suspense fallback={<PageSkeleton />}>
        <PerformanceContent band={band} bandName={bandEntry.displayName} />
      </Suspense>
    </div>
  );
}

async function PerformanceContent({ band, bandName }: { band: string; bandName: string }) {
  // The accuracy window is keyed on today's date, so it is resolved per request.
  await connection();
  const state = await getRecentAccuracy(band, 50, getEasternTodayIso());

  if (state.status !== "ready") {
    return (
      <DataGate
        state={state}
        missingEnvBody="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the performance route."
        errorTitle="Performance query failed"
        emptyTitle="No accuracy rows available"
        emptyBody="No accuracy rows were returned from the accuracy table."
      />
    );
  }

  const recall10Values: Array<number | null> = [];
  const recall25Values: Array<number | null> = [];
  const recall50Values: Array<number | null> = [];
  const p10Values: Array<number | null> = [];
  const p25Values: Array<number | null> = [];
  const p50Values: Array<number | null> = [];

  for (const row of state.rows) {
    recall10Values.push(row.recall10);
    recall25Values.push(row.recall25);
    recall50Values.push(row.recall50);
    p10Values.push(row.p10);
    p25Values.push(row.p25);
    p50Values.push(row.p50);
  }

  const top10Average = average(recall10Values);
  const top25Average = average(recall25Values);
  const top50Average = average(recall50Values);
  const p10Average = average(p10Values);
  const p25Average = average(p25Values);
  const p50Average = average(p50Values);
  const latestRow = state.rows[0] ?? null;
  const recentRows = state.rows.slice(0, 5);
  const averageMetrics: PerformanceMetric[] = [
    { label: "Top 10", coverage: top10Average, avgHits: p10Average, k: 10 },
    { label: "Top 25", coverage: top25Average, avgHits: p25Average, k: 25 },
    { label: "Top 50", coverage: top50Average, avgHits: p50Average, k: 50 },
  ];
  const latestMetrics: PerformanceMetric[] = [
    {
      label: "Top 10",
      coverage: latestRow?.recall10 ?? null,
      avgHits: latestRow?.p10 ?? null,
      k: 10,
    },
    {
      label: "Top 25",
      coverage: latestRow?.recall25 ?? null,
      avgHits: latestRow?.p25 ?? null,
      k: 25,
    },
    {
      label: "Top 50",
      coverage: latestRow?.recall50 ?? null,
      avgHits: latestRow?.p50 ?? null,
      k: 50,
    },
  ];

  return (
    <>
      <PageHero
        kicker="Accuracy desk"
        title={
          <>
            <span className="text-accent-text">{bandName}</span>
            <br />
            performance ledger
          </>
        }
        meta={`last ${state.rows.length} scored shows`}
        description="Track how much of each setlist the model's top-ranked groups actually capture."
        aside={
          <div className="rounded-xl border border-line bg-surface p-5">
            <p className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
              Latest scored show
            </p>
            <p className="mt-1 text-2xl font-bold tabular-nums text-on-surface">
              {formatMMDDYYYY(latestRow?.showDate ?? null)}
            </p>
            <p className="text-sm text-on-surface-variant">
              {latestRow?.venueName ?? "Venue unavailable"}
            </p>
            <dl className="mt-4 grid gap-2 border-t border-line pt-4">
              {latestMetrics.map((metric) => (
                <div key={metric.label} className="flex items-baseline justify-between gap-3">
                  <dt className="text-sm font-semibold text-on-surface">{metric.label}</dt>
                  <dd className="text-sm tabular-nums text-on-surface-variant">
                    <span className="font-bold text-on-surface">{formatPercent(metric.coverage)}</span>{" "}
                    coverage, {formatHits(metric.avgHits, metric.k)} hits
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        }
      />

      <section aria-label="Average accuracy" className="grid gap-4 md:grid-cols-3">
        {averageMetrics.map((metric) => (
          <CoverageMetricCard key={metric.label} metric={metric} tone="accent" />
        ))}
      </section>

      <section className="editorial-panel p-5 md:p-6">
        <h2 className="text-xl font-bold text-on-surface">Accuracy Over Time</h2>
        <p className="mb-5 mt-1 text-sm text-on-surface-variant">
          Each dot is one scored show, oldest on the left. The dashed line marks the average across the retained window.
        </p>
        <PerformanceChartPanel rows={state.rows} />
      </section>

      <SectionCard title="Recent Show Accuracy">
        <div className="space-y-4 md:hidden">
          <div className="grid gap-3">
            {recentRows.map((row, index) => (
              <div
                key={`${row.showDate}-${index}`}
                className="rounded-xl border border-line bg-surface-2 p-4"
              >
                <p className="text-lg font-bold tabular-nums text-on-surface">
                  {formatMMDDYYYY(row.showDate)}
                </p>
                <p className="text-sm text-on-surface-variant">
                  {row.venueName ?? "Venue unavailable"}
                </p>
                <div className="mt-3 grid gap-3 min-[520px]:grid-cols-3">
                  <CoverageMetricCard
                    metric={{ label: "Top 10", coverage: row.recall10, avgHits: row.p10, k: 10 }}
                    hitsPrefix=""
                  />
                  <CoverageMetricCard
                    metric={{ label: "Top 25", coverage: row.recall25, avgHits: row.p25, k: 25 }}
                    hitsPrefix=""
                  />
                  <CoverageMetricCard
                    metric={{ label: "Top 50", coverage: row.recall50, avgHits: row.p50, k: 50 }}
                    hitsPrefix=""
                  />
                </div>
              </div>
            ))}
          </div>

          <ExpandablePanel
            expandLabel="Open Raw Ledger"
            bodyClassName="px-3 pt-3"
            buttonClassName="w-full px-4 py-3 text-center text-sm font-bold text-on-surface"
            containerClassName="rounded-xl border border-line bg-surface-2"
          >
            <AccuracyTable rows={state.rows} band={state.band} />
          </ExpandablePanel>
        </div>

        <div className="hidden md:block">
          <AccuracyTable rows={state.rows} band={state.band} />
        </div>
      </SectionCard>
    </>
  );
}
