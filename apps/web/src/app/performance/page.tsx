import type { Metadata } from "next";
import { Suspense } from "react";
import { AccuracyTable } from "@/components/accuracy-table";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { ExpandablePanel } from "@/components/expandable-panel";
import { KToggle } from "@/components/k-toggle";
import { PageHero } from "@/components/page-hero";
import { RecallChart } from "@/components/recall-chart";
import { SectionCard } from "@/components/section-card";
import { getBands, getRecentAccuracy, bandEntryBySlug, resolveBandSelection } from "@/lib/data";
import { average, formatAvgHits, formatCompactDateLabel, formatPercent } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    k?: string;
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

type KSelection = 10 | 25 | 50 | "all";

function normalizeK(value?: string): KSelection {
  if (value === "all") {
    return "all";
  }

  const n = Number(value);
  return n === 10 || n === 25 || n === 50 ? n : "all";
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
        body="No accuracy rows were returned from the accuracy table."
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;
  const k = normalizeK(params.k);
  const activeMetric = k === "all" ? null : k;

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

            <div className="mt-6 grid grid-cols-3 gap-3 border-t border-outline-variant/15 pt-4 text-left">
              <div className="rounded-2xl bg-surface/70 px-3 py-3">
                <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">Top 10</p>
                <p className={`mt-1 font-headline text-lg font-bold ${activeMetric === 10 ? "text-primary" : "text-on-surface"}`}>
                  {formatPercent(latestRow?.recall10 ?? null)}
                </p>
                <p className="mt-0.5 font-label text-[8px] uppercase tracking-[0.12rem] text-on-surface-variant/60">
                  {formatAvgHits(latestRow?.p10 ?? null, 10)} hits
                </p>
              </div>
              <div className="rounded-2xl bg-surface/70 px-3 py-3">
                <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">Top 25</p>
                <p className={`mt-1 font-headline text-lg font-bold ${activeMetric === 25 ? "text-primary" : "text-on-surface"}`}>
                  {formatPercent(latestRow?.recall25 ?? null)}
                </p>
                <p className="mt-0.5 font-label text-[8px] uppercase tracking-[0.12rem] text-on-surface-variant/60">
                  {formatAvgHits(latestRow?.p25 ?? null, 25)} hits
                </p>
              </div>
              <div className="rounded-2xl bg-surface/70 px-3 py-3">
                <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">Top 50</p>
                <p className={`mt-1 font-headline text-lg font-bold ${activeMetric === 50 ? "text-primary" : "text-on-surface"}`}>
                  {formatPercent(latestRow?.recall50 ?? null)}
                </p>
                <p className="mt-0.5 font-label text-[8px] uppercase tracking-[0.12rem] text-on-surface-variant/60">
                  {formatAvgHits(latestRow?.p50 ?? null, 50)} hits
                </p>
              </div>
            </div>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        {[
          { label: "Top 10", coverage: top10Average, avgHits: p10Average, k: 10 },
          { label: "Top 25", coverage: top25Average, avgHits: p25Average, k: 25 },
          { label: "Top 50", coverage: top50Average, avgHits: p50Average, k: 50 },
        ].map((metric) => (
          <SectionCard
            key={metric.label}
            title={formatPercent(metric.coverage)}
            eyebrow={`${metric.label} coverage`}
            centered
          >
            <p className="text-center font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
              {formatAvgHits(metric.avgHits, metric.k)} avg. hits
            </p>
          </SectionCard>
        ))}
      </section>

      <p className="px-2 text-center text-sm text-on-surface-variant">
        Coverage is the share of the actual setlist in each Top-X group; avg. hits is the average number of picks that were played.
      </p>

      <SectionCard title="Accuracy Over Time">
        <div className="mb-4">
          <Suspense fallback={null}>
            <KToggle currentK={k} />
          </Suspense>
        </div>
        <RecallChart rows={state.rows} k={k} />
      </SectionCard>

      <SectionCard title="Recent Show Accuracy">
        <div className="space-y-4 md:hidden">
          <div className="grid gap-3">
            {recentRows.map((row, index) => (
              <div
                key={`${row.showDate}-${index}`}
                className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-headline text-lg font-semibold text-on-surface">
                      {formatCompactDateLabel(row.showDate)}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-on-surface-variant">
                      {row.venueName ?? "Venue unavailable"}
                    </p>
                  </div>
                  <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 font-label text-[10px] uppercase tracking-[0.18em] text-primary">
                    {formatPercent(row.recall10)} top 10
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2">
                  <div className="rounded-2xl bg-surface/70 px-3 py-3 text-center">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Top 10
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-primary">
                      {formatPercent(row.recall10)}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-surface/70 px-3 py-3 text-center">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Top 25
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-on-surface">
                      {formatPercent(row.recall25)}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-surface/70 px-3 py-3 text-center">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Top 50
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-on-surface">
                      {formatPercent(row.recall50)}
                    </p>
                  </div>
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
            <AccuracyTable rows={state.rows} />
          </ExpandablePanel>
        </div>

        <div className="hidden md:block">
          <AccuracyTable rows={state.rows} />
        </div>
      </SectionCard>
    </div>
  );
}
