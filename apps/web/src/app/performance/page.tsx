import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { AccuracyTable } from "@/components/accuracy-table";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { KToggle } from "@/components/k-toggle";
import { PageHero } from "@/components/page-hero";
import { RecallChart } from "@/components/recall-chart";
import { SectionCard } from "@/components/section-card";
import { MODEL_CONFIG, normalizeModel } from "@/lib/config";
import { getBands, getRecentAccuracy, bandEntryBySlug, resolveBandSelection } from "@/lib/data";
import { formatCompactDateLabel, formatPercent } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
    k?: string;
  }>;
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const model = normalizeModel(params.model);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;
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

type KSelection = 10 | 25 | 50 | "all";

function normalizeK(value?: string): KSelection {
  if (value === "all") {
    return "all";
  }

  const n = Number(value);
  return n === 10 || n === 25 || n === 50 ? n : "all";
}

function buildReplayHref(band: string, showDate: string | null) {
  if (!showDate) {
    return null;
  }

  return `/replay?band=${band}&date=${showDate}`;
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
  const state = await getRecentAccuracy(selectedBand, params.model, 50);

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

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;
  const k = normalizeK(params.k);
  const activeMetric = k === "all" ? null : k;

  const top10Average = average(state.rows.map((row) => row.k10Recall));
  const top25Average = average(state.rows.map((row) => row.k25Recall));
  const top50Average = average(state.rows.map((row) => row.k50Recall));
  const latestRow = state.rows[0] ?? null;
  const recentRows = state.rows.slice(0, 5);
  const latestReplayHref = buildReplayHref(state.band, latestRow?.showDate ?? null);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav
        band={state.band}
        model={state.model}
        bands={bands}
        pathname="/performance"
        compareHref={null}
      />

      <PageHero
        kicker="Accuracy desk"
        eyebrow=""
        title={`${bandName} performance ledger`}
        meta={`${MODEL_CONFIG[state.model].displayName} • last ${state.rows.length} scored shows`}
        description="Track how much of each setlist the model's top-ranked groups actually capture. This is the long-view read on stability, slippage, and standout nights."
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

            {latestReplayHref ? (
              <div className="mt-5 flex justify-center">
                <Link
                  href={latestReplayHref}
                  className="touch-manipulation inline-flex min-h-11 items-center justify-center rounded-full border border-outline-variant/30 bg-surface/75 px-4 py-2 font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
                >
                  View Replay
                </Link>
              </div>
            ) : null}

            <div className="mt-6 grid grid-cols-3 gap-3 border-t border-outline-variant/15 pt-4 text-left">
              <div className="rounded-2xl bg-surface/70 px-3 py-3">
                <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">Top 10</p>
                <p className={`mt-1 font-headline text-lg font-bold ${activeMetric === 10 ? "text-primary" : "text-on-surface"}`}>
                  {formatPercent(latestRow?.k10Recall ?? null)}
                </p>
              </div>
              <div className="rounded-2xl bg-surface/70 px-3 py-3">
                <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">Top 25</p>
                <p className={`mt-1 font-headline text-lg font-bold ${activeMetric === 25 ? "text-primary" : "text-on-surface"}`}>
                  {formatPercent(latestRow?.k25Recall ?? null)}
                </p>
              </div>
              <div className="rounded-2xl bg-surface/70 px-3 py-3">
                <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">Top 50</p>
                <p className={`mt-1 font-headline text-lg font-bold ${activeMetric === 50 ? "text-primary" : "text-on-surface"}`}>
                  {formatPercent(latestRow?.k50Recall ?? null)}
                </p>
              </div>
            </div>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <SectionCard
          title={formatPercent(top10Average)}
          eyebrow="Avg Top 10"
          centered
        />
        <SectionCard
          title={formatPercent(top25Average)}
          eyebrow="Avg Top 25"
          centered
        />
        <SectionCard
          title={formatPercent(top50Average)}
          eyebrow="Avg Top 50"
          centered
        />
      </section>

      <p className="px-2 text-center text-sm text-on-surface-variant">
        Accuracy is measured as the share of the actual setlist included in each Top-X group.
      </p>

      <SectionCard title={`${MODEL_CONFIG[state.model].displayName} Accuracy Over Time`}>
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
                    {formatPercent(row.k10Recall)} top 10
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-3 gap-2">
                  <div className="rounded-2xl bg-surface/70 px-3 py-3 text-center">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Top 10
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-primary">
                      {formatPercent(row.k10Recall)}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-surface/70 px-3 py-3 text-center">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Top 25
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-on-surface">
                      {formatPercent(row.k25Recall)}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-surface/70 px-3 py-3 text-center">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Top 50
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-on-surface">
                      {formatPercent(row.k50Recall)}
                    </p>
                  </div>
                </div>
                {buildReplayHref(state.band, row.showDate) ? (
                  <Link
                    href={buildReplayHref(state.band, row.showDate) ?? "#"}
                    className="touch-manipulation mt-4 inline-flex min-h-11 items-center justify-center rounded-full border border-outline-variant/30 bg-surface/75 px-4 py-2 font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
                  >
                    Replay Prediction
                  </Link>
                ) : null}
              </div>
            ))}
          </div>

          <details className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low">
            <summary className="cursor-pointer list-none px-4 py-4 font-headline text-sm uppercase tracking-[0.12em] text-on-surface">
              Open raw ledger
            </summary>
            <div className="px-3 pb-3">
              <AccuracyTable
                rows={state.rows}
                replayBand={state.band}
              />
            </div>
          </details>
        </div>

        <div className="hidden md:block">
          <AccuracyTable
            rows={state.rows}
            replayBand={state.band}
          />
        </div>
      </SectionCard>
    </div>
  );
}
