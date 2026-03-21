import type { Metadata } from "next";
import { Suspense } from "react";
import { AccuracyTable } from "@/components/accuracy-table";
import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { KToggle } from "@/components/k-toggle";
import { RecallChart } from "@/components/recall-chart";
import { SectionCard } from "@/components/section-card";
import { MODEL_CONFIG, normalizeModel } from "@/lib/config";
import { type AccuracyRow, getBands, getRecentAccuracy, bandEntryBySlug, resolveBandSelection } from "@/lib/data";
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

function getRecallForK(rows: AccuracyRow[], k: 10 | 25 | 50): Array<number | null> {
  return rows.map((row) => (k === 10 ? row.k10Recall : k === 25 ? row.k25Recall : row.k50Recall));
}

function getBestRecallRow(rows: AccuracyRow[], k: 10 | 25 | 50) {
  return rows.reduce<AccuracyRow | null>((best, row) => {
    const current = k === 10 ? row.k10Recall : k === 25 ? row.k25Recall : row.k50Recall;
    if (!best) return current !== null ? row : null;
    const bestVal = k === 10 ? best.k10Recall : k === 25 ? best.k25Recall : best.k50Recall;
    return current !== null && bestVal !== null && current > bestVal ? row : best;
  }, null);
}

function normalizeK(value?: string): 10 | 25 | 50 {
  const n = Number(value);
  return n === 10 || n === 25 || n === 50 ? n : 10;
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
  const state = await getRecentAccuracy(selectedBand, params.model, 20);

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

  const top10Average = average(state.rows.map((row) => row.k10Recall));
  const top25Average = average(state.rows.map((row) => row.k25Recall));
  const top50Average = average(state.rows.map((row) => row.k50Recall));
  const latestRow = state.rows[0] ?? null;
  const currentKValues = getRecallForK(state.rows, k);
  const recentWindow = average(currentKValues.slice(0, 5));
  const priorWindow = average(currentKValues.slice(5, 10));
  const trendDelta =
    recentWindow !== null && priorWindow !== null ? recentWindow - priorWindow : null;
  const bestRow = getBestRecallRow(state.rows, k);

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
              Top {k} recall{" "}
              {formatPercent(
                k === 10
                  ? latestRow?.k10Recall ?? null
                  : k === 25
                    ? latestRow?.k25Recall ?? null
                    : latestRow?.k50Recall ?? null
              )}
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <SectionCard
          title={formatPercent(top10Average)}
          eyebrow="Avg Top 10"
        >
          <p className="text-sm leading-6 text-on-surface-variant">
            Quick-hit prediction quality for the highest-confidence slice.
          </p>
        </SectionCard>
        <SectionCard
          title={formatPercent(top25Average)}
          eyebrow="Avg Top 25"
        >
          <p className="text-sm leading-6 text-on-surface-variant">
            Broader board coverage across the mid-ranked prediction set.
          </p>
        </SectionCard>
        <SectionCard
          title={formatPercent(top50Average)}
          eyebrow="Avg Top 50"
        >
          <p className="text-sm leading-6 text-on-surface-variant">
            Long-tail hit rate across the full recommendation window.
          </p>
        </SectionCard>
      </section>

      <SectionCard
        title={`Recall Timeline`}
        eyebrow={`Top-${k} accuracy over time`}
      >
        <div className="mb-4">
          <Suspense fallback={null}>
            <KToggle currentK={k} />
          </Suspense>
        </div>
        <RecallChart rows={state.rows} k={k} />
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <SectionCard title="Performance Read" eyebrow={`Top-${k} trend`}>
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

        <SectionCard title="Best Night" eyebrow={`Top-${k} peak`}>
          <div className="space-y-3">
            <p className="font-headline text-2xl font-semibold text-on-surface">
              {formatCompactDateLabel(bestRow?.showDate ?? null)}
            </p>
            <p className="text-sm text-on-surface-variant">
              {bestRow?.venueName ?? "Venue unavailable"}
            </p>
            <p className="text-sm text-primary">
              Top {k} recall{" "}
              {formatPercent(
                k === 10
                  ? bestRow?.k10Recall ?? null
                  : k === 25
                    ? bestRow?.k25Recall ?? null
                    : bestRow?.k50Recall ?? null
              )}
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
