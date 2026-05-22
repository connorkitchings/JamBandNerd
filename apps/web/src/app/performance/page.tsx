import type { Metadata } from "next";
import { Suspense } from "react";
import { AccuracyTable } from "@/components/accuracy-table";
import { ChartMetricToggle, type ChartMetric } from "@/components/chart-metric-toggle";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataGate } from "@/components/data-gate";
import { DataState } from "@/components/data-state";
import { ExpandablePanel } from "@/components/expandable-panel";
import { KToggle } from "@/components/k-toggle";
import { PageHero } from "@/components/page-hero";
import { RecallChart } from "@/components/recall-chart";
import { SectionCard } from "@/components/section-card";
import { getBands, getRecentAccuracy, bandEntryBySlug, resolveBandSelection } from "@/lib/data";
import { average, formatAvgHits, formatCompactDateLabel, formatHits, formatPercent } from "@/lib/format";

export const revalidate = 3600;

type Props = {
  searchParams: Promise<{
    band?: string;
    k?: string;
    metric?: string;
  }>;
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;

  return {
    title: `${bandName} Performance Ledger | JamBandNerd`,
    description: `Track historical prediction accuracy for ${bandName}.`,
  };
}

type KSelection = 10 | 25 | 50;
type PerformanceMetric = {
  label: string;
  coverage: number | null;
  avgHits: number | null;
  k: 10 | 25 | 50;
};

function normalizeK(value?: string): KSelection {
  const n = Number(value);
  return n === 25 || n === 50 ? n : 10;
}

function normalizeChartMetric(value?: string): ChartMetric {
  return value === "hits" ? "hits" : "coverage";
}

function PerformanceMetricCard({
  metric,
  active,
  compact = false,
  hitsLabel = "Avg. Hits",
}: {
  metric: PerformanceMetric;
  active?: boolean;
  compact?: boolean;
  hitsLabel?: "Avg. Hits" | "Hits";
}) {
  return (
    <div
      className={`rounded-2xl border px-4 py-4 text-center ${
        active
          ? "border-primary/30 bg-primary/10"
          : "border-outline-variant/15 bg-surface/70"
      }`}
    >
      <p className="font-headline text-base font-bold text-on-surface underline decoration-current decoration-2 underline-offset-4">
        {metric.label}
      </p>
      <div className={`mt-4 grid grid-cols-2 ${compact ? "gap-2" : "gap-4"}`}>
        <div>
          <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-tertiary">
            {hitsLabel}
          </p>
          <p
            className={`mt-1 font-headline font-bold text-tertiary ${
              compact ? "text-lg" : "text-2xl"
            }`}
          >
            {hitsLabel === "Hits"
              ? formatHits(metric.avgHits, metric.k)
              : formatAvgHits(metric.avgHits, metric.k)}
          </p>
        </div>
        <div>
          <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-primary">
            Coverage
          </p>
          <p
            className={`mt-1 font-headline font-bold text-primary ${
              compact ? "text-lg" : "text-2xl"
            }`}
          >
            {formatPercent(metric.coverage)}
          </p>
        </div>
      </div>
    </div>
  );
}

function LatestMetricSnapshot({
  metric,
  active,
}: {
  metric: PerformanceMetric;
  active?: boolean;
}) {
  return (
    <div
      className={`grid grid-cols-3 items-center gap-3 rounded-xl border px-3 py-2.5 text-center ${
        active
          ? "border-primary/30 bg-primary/10"
          : "border-outline-variant/15 bg-surface/65"
      }`}
    >
      <div>
        <p className="font-label text-[8px] font-semibold uppercase tracking-[0.12rem] text-tertiary">
          Hits
        </p>
        <p className="mt-0.5 font-headline text-base font-bold text-tertiary">
          {formatHits(metric.avgHits, metric.k)}
        </p>
      </div>
      <p className="font-headline text-sm font-bold text-on-surface underline decoration-current decoration-2 underline-offset-4">
        {metric.label}
      </p>
      <div>
        <p className="font-label text-[8px] font-semibold uppercase tracking-[0.12rem] text-primary">
          Coverage
        </p>
        <p className="mt-0.5 font-headline text-base font-bold text-primary">
          {formatPercent(metric.coverage)}
        </p>
      </div>
    </div>
  );
}

export default async function PerformancePage({ searchParams }: Props) {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  if (bandsResult.status === "ready" && bandSelection.isInvalid) {
    return (
      <DataState
        title="Band not found"
        body={`No active band found for slug "${bandSelection.requestedSlug}". Select a supported band from the navigation.`}
      />
    );
  }

  const selectedBand =
    bandsResult.status === "ready" ? bandSelection.bandEntry?.slug : params.band;
  const state = await getRecentAccuracy(selectedBand, 50);

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

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;
  const k = normalizeK(params.k);
  const chartMetric = normalizeChartMetric(params.metric);

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
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav
        band={state.band}
        bands={bands}
        pathname="/performance"
      />

      <PageHero
        kicker="Accuracy desk"
        eyebrow=""
        title={`${bandName} performance ledger`}
        meta={`last ${state.rows.length} scored shows`}
        description="Track how much of each setlist the model's top-ranked groups actually capture. This is the long-view read on stability, variation, and standout nights."
        aside={
          <div className="editorial-panel p-5">
            <div className="space-y-1 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Latest scored show
              </p>
              <p className="font-headline text-2xl font-semibold text-on-surface">
                {formatCompactDateLabel(latestRow?.showDate ?? null)}
              </p>
              <p className="text-sm text-on-surface-variant">
                {latestRow?.venueName ?? "Venue unavailable"}
              </p>
            </div>

            <div className="mt-4 grid gap-2 border-t border-outline-variant/15 pt-4">
              {latestMetrics.map((metric) => (
                <LatestMetricSnapshot
                  key={metric.label}
                  metric={metric}
                />
              ))}
            </div>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        {averageMetrics.map((metric) => (
          <PerformanceMetricCard
            key={metric.label}
            metric={metric}
          />
        ))}
      </section>

      <p className="px-2 text-center text-sm text-on-surface-variant">
        Coverage is the share of the actual setlist caught in each Top-X group. Avg. Hits is the average number of picks played.
      </p>

      <section className="editorial-panel p-5 md:p-7">
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-start">
          <div>
            <h2 className="font-headline text-[1.35rem] font-semibold uppercase tracking-[-0.03em] text-on-surface md:text-2xl">
              Accuracy Over Time
            </h2>
            <p className="mt-2 max-w-xl text-sm leading-6 text-on-surface-variant">
              Each dot is one scored show. The dashed line marks the average across the retained window.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-[auto_auto] sm:items-start lg:justify-end">
            <div className="space-y-1.5">
              <p className="font-label text-[9px] font-semibold uppercase tracking-[0.18em] text-on-surface-variant">
                Measure
              </p>
              <Suspense fallback={null}>
                <ChartMetricToggle currentMetric={chartMetric} />
              </Suspense>
            </div>
            <div className="space-y-1.5">
              <p className="font-label text-[9px] font-semibold uppercase tracking-[0.18em] text-on-surface-variant">
                Prediction Group
              </p>
              <Suspense fallback={null}>
                <KToggle currentK={k} />
              </Suspense>
            </div>
          </div>
        </div>
        <div className="mt-5">
          <RecallChart rows={state.rows} k={k} metric={chartMetric} />
        </div>
      </section>

      <SectionCard title="Recent Show Accuracy">
        <div className="space-y-4 md:hidden">
          <div className="grid gap-3">
            {recentRows.map((row, index) => (
              <div
                key={`${row.showDate}-${index}`}
                className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4"
              >
                <div className="text-center">
                  <div>
                    <p className="font-headline text-lg font-semibold text-on-surface">
                      {formatCompactDateLabel(row.showDate)}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-on-surface-variant">
                      {row.venueName ?? "Venue unavailable"}
                    </p>
                  </div>
                </div>
                <div className="mt-4 grid gap-2 min-[520px]:grid-cols-3">
                  <PerformanceMetricCard
                    metric={{
                      label: "Top 10",
                      coverage: row.recall10,
                      avgHits: row.p10,
                      k: 10,
                    }}
                    compact
                    hitsLabel="Hits"
                  />
                  <PerformanceMetricCard
                    metric={{
                      label: "Top 25",
                      coverage: row.recall25,
                      avgHits: row.p25,
                      k: 25,
                    }}
                    compact
                    hitsLabel="Hits"
                  />
                  <PerformanceMetricCard
                    metric={{
                      label: "Top 50",
                      coverage: row.recall50,
                      avgHits: row.p50,
                      k: 50,
                    }}
                    compact
                    hitsLabel="Hits"
                  />
                </div>
              </div>
            ))}
          </div>

          <ExpandablePanel
            expandLabel="Open Raw Ledger"
            bodyClassName="px-3 pt-3"
            buttonClassName="w-full rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4 text-center font-headline text-sm uppercase tracking-[0.12em] text-on-surface"
            containerClassName="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low"
          >
            <AccuracyTable rows={state.rows} band={state.band} />
          </ExpandablePanel>
        </div>

        <div className="hidden md:block">
          <AccuracyTable rows={state.rows} band={state.band} />
        </div>
      </SectionCard>
    </div>
  );
}
