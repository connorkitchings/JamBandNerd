import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { AccuracyTable } from "@/components/accuracy-table";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataGate } from "@/components/data-gate";
import { ExpandablePanel } from "@/components/expandable-panel";
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
      className={`rounded-xl border px-3 py-3 text-center md:px-4 ${
        active
          ? "border-primary/30 bg-primary/10"
          : "border-outline-variant/15 bg-surface/35"
      }`}
    >
      <div className="border-b border-outline-variant/15 pb-2">
        <p className="font-headline text-base font-bold text-on-surface underline decoration-current decoration-2 underline-offset-4 md:text-lg">
          {metric.label}
        </p>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 md:gap-3">
        <div className="rounded-lg bg-surface-container-low/55 px-2.5 py-2.5 md:rounded-xl md:px-3">
          <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-tertiary">
            {hitsLabel}
          </p>
          <p
            className={`mt-0.5 font-headline font-bold leading-none text-tertiary ${
              compact ? "text-xl" : "text-2xl md:text-3xl"
            }`}
          >
            {hitsLabel === "Hits"
              ? formatHits(metric.avgHits, metric.k)
              : formatAvgHits(metric.avgHits, metric.k)}
          </p>
          <p className="mt-1 text-[11px] leading-4 text-on-surface-variant md:text-xs md:leading-5">
            picks played
          </p>
        </div>
        <div className="rounded-lg bg-surface-container-low/55 px-2.5 py-2.5 md:rounded-xl md:px-3">
          <p className="font-label text-[9px] font-semibold uppercase tracking-[0.14rem] text-primary">
            Coverage
          </p>
          <p
            className={`mt-0.5 font-headline font-bold leading-none text-primary ${
              compact ? "text-xl" : "text-2xl md:text-3xl"
            }`}
          >
            {formatPercent(metric.coverage)}
          </p>
          <p className="mt-1 text-[11px] leading-4 text-on-surface-variant md:text-xs md:leading-5">
            setlist caught
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
            <span className="text-primary">{bandName}</span>
            <br />
            performance ledger
          </>
        }
        meta={`last ${state.rows.length} scored shows`}
        description="Track how much of each setlist the model's top-ranked groups actually capture."
        aside={
          <div className="editorial-panel p-5">
            <div className="space-y-1 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Latest scored show
              </p>
              <p className="font-headline text-2xl font-semibold text-on-surface">
                {formatMMDDYYYY(latestRow?.showDate ?? null)}
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


      <section className="editorial-panel p-5 md:p-7">
        <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-start">
          <div className="text-center lg:text-left">
            <h2 className="font-headline text-[1.35rem] font-semibold uppercase tracking-[-0.03em] text-on-surface md:text-2xl">
              Accuracy Over Time
            </h2>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">
              Each dot is one scored show. The dashed line marks the average across the retained window.
            </p>
          </div>
          <PerformanceChartPanel rows={state.rows} />
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
                      {formatMMDDYYYY(row.showDate)}
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
    </>
  );
}
