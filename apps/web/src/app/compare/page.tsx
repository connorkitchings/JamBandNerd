import type { Metadata } from "next";
import Link from "next/link";
import { CompareMetricSelect } from "@/components/compare-metric-select";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { ExpandablePanel } from "@/components/expandable-panel";
import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";
import { getBands, bandEntryBySlug, resolveBandSelection, getRecentAccuracy } from "@/lib/data";
import { ACTIVE_MODELS, MODEL_CONFIG, type ModelSlug } from "@/lib/config";
import { buildLocationLabel, formatCompactDateLabel, formatPercent } from "@/lib/format";

export const dynamic = "force-dynamic";

const COMPARISON_WINDOW = 50;
const COMPARISON_METRIC_OPTIONS = [10, 25, 50] as const;
const DEFAULT_COMPARISON_METRIC: ComparisonMetric = 10;

type ComparisonMetric = (typeof COMPARISON_METRIC_OPTIONS)[number];

type Props = {
  searchParams: Promise<{
    band?: string;
    modelA?: string;
    modelB?: string;
    k?: string;
  }>;
};

function WinnerCrown({ tone, side }: { tone: "primary" | "tertiary"; side: "left" | "right" }) {
  const toneClasses =
    tone === "primary"
      ? "border-primary/35 bg-primary/12 text-primary shadow-[0_8px_18px_rgba(255,191,105,0.18)]"
      : "border-tertiary/35 bg-tertiary/10 text-tertiary shadow-[0_8px_18px_rgba(136,229,216,0.16)]";
  const sideClasses =
    side === "left"
      ? "left-0 -translate-x-[22%]"
      : "right-0 translate-x-[22%]";

  return (
    <span
      aria-label="Winner"
      className={`absolute top-0 flex size-7 -translate-y-[28%] items-center justify-center rounded-full border ${toneClasses} ${sideClasses}`}
    >
      <svg aria-hidden="true" className="size-4" viewBox="0 0 24 24">
        <path
          d="M4.5 18.5H19.5L18 9.5L14 12.2L12 5.5L10 12.2L6 9.5L4.5 18.5Z"
          fill="currentColor"
        />
      </svg>
    </span>
  );
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;

  const modelA = params.modelA ?? ACTIVE_MODELS[0] ?? "notebook";
  const modelB = params.modelB ?? ACTIVE_MODELS[1] ?? ACTIVE_MODELS[0] ?? "notebook";
  const labelA = MODEL_CONFIG[modelA as ModelSlug]?.displayName ?? "Model A";
  const labelB = MODEL_CONFIG[modelB as ModelSlug]?.displayName ?? "Model B";

  return {
    title: `${bandName} Model Compare | JamBandNerd`,
    description: `Compare ${labelA} vs ${labelB} across the last ${COMPARISON_WINDOW} scored shows for ${bandName}.`,
  };
}

function averageMetric(values: Array<number | null>) {
  const presentValues = values.filter((value): value is number => value !== null);
  if (presentValues.length === 0) {
    return null;
  }

  return presentValues.reduce((sum, value) => sum + value, 0) / presentValues.length;
}

function buildReplayHref(band: string | null | undefined, showDate: string | null) {
  if (!band || !showDate) {
    return null;
  }

  return `/replay?band=${band}&date=${showDate}`;
}

function resolveComparisonMetric(value: string | undefined): ComparisonMetric {
  const requestedMetric = Number(value);
  if (requestedMetric === 10 || requestedMetric === 25 || requestedMetric === 50) {
    return requestedMetric;
  }

  return DEFAULT_COMPARISON_METRIC;
}

function getSelectedMetric(
  row: {
    nb10: number | null;
    nb25: number | null;
    nb50: number | null;
    ck10: number | null;
    ck25: number | null;
    ck50: number | null;
  },
  model: "nb" | "ck",
  metric: ComparisonMetric,
) {
  if (model === "nb") {
    return metric === 10 ? row.nb10 : metric === 25 ? row.nb25 : row.nb50;
  }

  return metric === 10 ? row.ck10 : metric === 25 ? row.ck25 : row.ck50;
}

export default async function ComparePage({ searchParams }: Props) {
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
  const modelASlug = (ACTIVE_MODELS.includes(params.modelA as ModelSlug) ? params.modelA : ACTIVE_MODELS[0]) as ModelSlug;
  const modelBSlug = (ACTIVE_MODELS.includes(params.modelB as ModelSlug) ? params.modelB : (ACTIVE_MODELS[1] ?? ACTIVE_MODELS[0])) as ModelSlug;
  const comparisonMetric = resolveComparisonMetric(params.k);

  const labelA = MODEL_CONFIG[modelASlug].displayName;
  const labelB = MODEL_CONFIG[modelBSlug].displayName;

  const [notebookPerf, secondaryPerf] = await Promise.all([
    getRecentAccuracy(selectedBand, modelASlug, COMPARISON_WINDOW),
    getRecentAccuracy(selectedBand, modelBSlug, COMPARISON_WINDOW),
  ]);

  if (notebookPerf.status === "missing_env" || secondaryPerf.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the comparison route."
      />
    );
  }

  if (notebookPerf.status !== "ready" || secondaryPerf.status !== "ready") {
    return (
      <DataState
        title="Comparison data unavailable"
        body="Historical accuracy rows were not available for both selected models."
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, selectedBand ?? "");
  const bandName = bandEntry?.displayName ?? selectedBand ?? "Band";

  const nbRows = notebookPerf.status === "ready" ? notebookPerf.rows : [];
  const ckRows = secondaryPerf.status === "ready" ? secondaryPerf.rows : [];
  
  const sharedDates = new Set([...nbRows.map(r => r.showDate), ...ckRows.map(r => r.showDate)]);
  const headToHeadRows = Array.from(sharedDates)
    .filter((date): date is string => date !== null)
    .map(date => {
      const nbRow = nbRows.find(r => r.showDate === date);
      const ckRow = ckRows.find(r => r.showDate === date);
      if (!nbRow || !ckRow) {
        return null;
      }

      return {
        date,
        venueName: nbRow.venueName ?? ckRow.venueName ?? "Unknown Venue",
        city: nbRow.city ?? ckRow.city ?? null,
        state: nbRow.state ?? ckRow.state ?? null,
        nb10: nbRow.k10Recall ?? null,
        nb25: nbRow.k25Recall ?? null,
        nb50: nbRow.k50Recall ?? null,
        nbPrec10: nbRow.k10Precision ?? null,
        nbPrec25: nbRow.k25Precision ?? null,
        nbPrec50: nbRow.k50Precision ?? null,
        ck10: ckRow.k10Recall ?? null,
        ck25: ckRow.k25Recall ?? null,
        ck50: ckRow.k50Recall ?? null,
        ckPrec10: ckRow.k10Precision ?? null,
        ckPrec25: ckRow.k25Precision ?? null,
        ckPrec50: ckRow.k50Precision ?? null,
      };
    })
    .filter((row): row is NonNullable<typeof row> => row !== null)
    .sort((a, b) => b.date.localeCompare(a.date));

  let nbWins = 0;
  let ckWins = 0;
  let ties = 0;

  headToHeadRows.forEach(r => {
    const notebookValue = getSelectedMetric(r, "nb", comparisonMetric);
    const secondaryValue = getSelectedMetric(r, "ck", comparisonMetric);
    if (notebookValue === null || secondaryValue === null) {
      return;
    }

    if (notebookValue > secondaryValue) nbWins++;
    else if (secondaryValue > notebookValue) ckWins++;
    else ties++;
  });

  const mobileHeadToHeadRows = headToHeadRows.slice(0, 5);
  const remainingHeadToHeadRows = headToHeadRows.slice(5);
  const averageHeadToHeadRow =
    headToHeadRows.length > 0
      ? {
          date: "average",
          venueName: "",
          city: null,
          state: null,
          nb10: averageMetric(headToHeadRows.map((row) => row.nb10)),
          nb25: averageMetric(headToHeadRows.map((row) => row.nb25)),
          nb50: averageMetric(headToHeadRows.map((row) => row.nb50)),
          nbPrec10: averageMetric(headToHeadRows.map((row) => row.nbPrec10)),
          nbPrec25: averageMetric(headToHeadRows.map((row) => row.nbPrec25)),
          nbPrec50: averageMetric(headToHeadRows.map((row) => row.nbPrec50)),
          ck10: averageMetric(headToHeadRows.map((row) => row.ck10)),
          ck25: averageMetric(headToHeadRows.map((row) => row.ck25)),
          ck50: averageMetric(headToHeadRows.map((row) => row.ck50)),
          ckPrec10: averageMetric(headToHeadRows.map((row) => row.ckPrec10)),
          ckPrec25: averageMetric(headToHeadRows.map((row) => row.ckPrec25)),
          ckPrec50: averageMetric(headToHeadRows.map((row) => row.ckPrec50)),
        }
      : null;
  const headToHeadLedgerRows = averageHeadToHeadRow
    ? [averageHeadToHeadRow, ...headToHeadRows]
    : headToHeadRows;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav
        band={selectedBand ?? modelASlug}
        model={modelASlug}
        bands={bands}
        pathname="/compare"
        hideSecondary
        bandLinks={bands.map((item) => ({
          href: `/compare?band=${item.slug}&modelA=${modelASlug}&modelB=${modelBSlug}&k=${comparisonMetric}`,
          label: item.displayName,
          active: item.slug === selectedBand,
        }))}
      />

      <PageHero
        kicker="Historical Performance"
        eyebrow=""
        title={`${bandName} comparison board`}
        meta={`${labelA} vs ${labelB} • last ${COMPARISON_WINDOW} scored shows`}
        description={`Track ${labelA} versus ${labelB} across the recent scoring window and read where one model has been outperforming the other over time.`}
        descriptionClassName="max-w-5xl"
      />

      <section className="editorial-chip flex flex-col gap-3 rounded-[1.5rem] p-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-1">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
            Top-X Threshold
          </p>
          <p className="text-sm leading-6 text-on-surface-variant">
            Choose which threshold to compare by.
          </p>
        </div>
        <CompareMetricSelect
          selectedMetric={comparisonMetric}
          options={[...COMPARISON_METRIC_OPTIONS]}
        />
      </section>

      <section className="grid grid-cols-3 gap-3 md:gap-4">
        <div className="editorial-panel px-3 py-4 text-center md:p-6">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
            <span className="block">{labelA}</span>
            <span className="block">Wins</span>
          </p>
          <p className="mt-2 font-headline text-2xl font-bold text-primary md:mt-3 md:text-4xl">{nbWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-{comparisonMetric} accuracy match-ups</p>
        </div>
        <div className="editorial-panel px-3 py-4 text-center md:p-6">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
            <span className="block">{labelB}</span>
            <span className="block">Wins</span>
          </p>
          <p className="mt-2 font-headline text-2xl font-bold text-tertiary md:mt-3 md:text-4xl">{ckWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-{comparisonMetric} accuracy match-ups</p>
        </div>
        <div className="editorial-panel px-3 py-4 text-center md:p-6">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
            <span className="block">Ties</span>
            <span className="block">&nbsp;</span>
          </p>
          <p className="mt-2 font-headline text-2xl font-bold text-on-surface md:mt-3 md:text-4xl">{ties}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Identical Top-{comparisonMetric} accuracy</p>
        </div>
      </section>

      {headToHeadRows.length > 0 && (
        <SectionCard title="Historical Performance">
          <div className="space-y-4 md:hidden">
            {mobileHeadToHeadRows.map((row) => {
              const notebookValue = getSelectedMetric(row, "nb", comparisonMetric);
              const secondaryValue = getSelectedMetric(row, "ck", comparisonMetric);
              const isNbWin =
                notebookValue !== null && secondaryValue !== null && notebookValue > secondaryValue;
              const isCkWin =
                notebookValue !== null && secondaryValue !== null && secondaryValue > notebookValue;
              const replayHref = buildReplayHref(selectedBand, row.date);
              const locationLabel = buildLocationLabel([row.city, row.state]);

              return (
                <div
                  key={row.date}
                  className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4"
                >
                  <div className="flex items-center justify-between gap-4 pt-1">
                    <p className="shrink-0 font-headline text-lg font-semibold text-on-surface">
                      {formatCompactDateLabel(row.date)}
                    </p>
                    <div className="min-w-0 text-right">
                      <p className="text-xs leading-5 text-on-surface-variant">
                        {row.venueName || "Venue unavailable"}
                      </p>
                      <p className="text-xs leading-5 text-on-surface-variant">
                        {locationLabel || "Location unavailable"}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-3">
                    <div className="relative rounded-2xl bg-surface/70 px-3 py-3 text-center">
                      {isNbWin ? <WinnerCrown tone="primary" side="left" /> : null}
                      <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                        {labelA}
                      </p>
                      <p className="mt-1 font-headline text-base font-bold text-primary">
                        {formatPercent(notebookValue)}
                      </p>
                    </div>
                    <div className="relative rounded-2xl bg-surface/70 px-3 py-3 text-center">
                      {isCkWin ? <WinnerCrown tone="tertiary" side="right" /> : null}
                      <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                        {labelB}
                      </p>
                      <p className="mt-1 font-headline text-base font-bold text-tertiary">
                        {formatPercent(secondaryValue)}
                      </p>
                    </div>
                  </div>

                  {!isNbWin && !isCkWin ? (
                    <p className="mt-3 text-center font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Tie
                    </p>
                  ) : null}

                  {replayHref ? (
                    <div className="mt-4 flex justify-center">
                      <Link
                        href={replayHref}
                        className="touch-manipulation inline-flex min-h-11 w-full items-center justify-center rounded-full border border-outline-variant/30 bg-surface/75 px-4 py-2 font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
                      >
                        View Replay
                      </Link>
                    </div>
                  ) : null}
                </div>
              );
            })}

            {remainingHeadToHeadRows.length > 0 ? (
              <ExpandablePanel
                bodyClassName="space-y-4 px-3 pt-3"
                buttonClassName="w-full rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4 text-center font-headline text-sm uppercase tracking-[0.12em] text-on-surface"
                containerClassName="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low"
              >
                  {remainingHeadToHeadRows.map((row) => {
                    const notebookValue = getSelectedMetric(row, "nb", comparisonMetric);
                    const secondaryValue = getSelectedMetric(row, "ck", comparisonMetric);
                    const isNbWin =
                      notebookValue !== null && secondaryValue !== null && notebookValue > secondaryValue;
                    const isCkWin =
                      notebookValue !== null && secondaryValue !== null && secondaryValue > notebookValue;
                    const replayHref = buildReplayHref(selectedBand, row.date);
                    const locationLabel = buildLocationLabel([row.city, row.state]);

                    return (
                      <div
                        key={row.date}
                        className="rounded-[1.2rem] border border-outline-variant/20 bg-surface/70 px-4 py-4"
                      >
                        <div className="flex items-center justify-between gap-4 pt-1">
                          <p className="shrink-0 font-headline text-lg font-semibold text-on-surface">
                            {formatCompactDateLabel(row.date)}
                          </p>
                          <div className="min-w-0 text-right">
                            <p className="text-xs leading-5 text-on-surface-variant">
                              {row.venueName || "Venue unavailable"}
                            </p>
                            <p className="text-xs leading-5 text-on-surface-variant">
                              {locationLabel || "Location unavailable"}
                            </p>
                          </div>
                        </div>

                        <div className="mt-5 grid grid-cols-2 gap-3">
                          <div className="relative rounded-2xl bg-surface-container px-3 py-3 text-center">
                            {isNbWin ? <WinnerCrown tone="primary" side="left" /> : null}
                            <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                              {labelA}
                            </p>
                            <p className="mt-1 font-headline text-base font-bold text-primary">
                              {formatPercent(notebookValue)}
                            </p>
                          </div>
                          <div className="relative rounded-2xl bg-surface-container px-3 py-3 text-center">
                            {isCkWin ? <WinnerCrown tone="tertiary" side="right" /> : null}
                            <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                              {labelB}
                            </p>
                            <p className="mt-1 font-headline text-base font-bold text-tertiary">
                              {formatPercent(secondaryValue)}
                            </p>
                          </div>
                        </div>

                        {!isNbWin && !isCkWin ? (
                          <p className="mt-3 text-center font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                            Tie
                          </p>
                        ) : null}

                        {replayHref ? (
                          <div className="mt-4 flex justify-center">
                            <Link
                              href={replayHref}
                              className="touch-manipulation inline-flex min-h-11 w-full items-center justify-center rounded-full border border-outline-variant/30 bg-surface/75 px-4 py-2 font-headline text-[10px] uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
                            >
                              View Replay
                            </Link>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
              </ExpandablePanel>
            ) : null}
          </div>

          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead>
                <tr className="border-b border-outline-variant/20 bg-surface-container-low">
                  <th className="py-3 px-4 font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Show Date</th>
                  <th className="py-3 px-4 font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Venue</th>
                  <th className="py-3 px-4 font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Location</th>
                  <th className="py-3 px-4 text-center font-label uppercase tracking-wider text-primary text-[10px] font-semibold">
                    {labelA} Top {comparisonMetric}
                  </th>
                  <th className="py-3 px-4 text-center font-label uppercase tracking-wider text-tertiary text-[10px] font-semibold">
                    {labelB} Top {comparisonMetric}
                  </th>
                  <th className="py-3 px-4 text-right font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Winner</th>
                </tr>
              </thead>
              <tbody>
                {headToHeadLedgerRows.map((row) => {
                  const isAverageRow = row.date === "average";
                  const notebookValue = getSelectedMetric(row, "nb", comparisonMetric);
                  const secondaryValue = getSelectedMetric(row, "ck", comparisonMetric);
                  const isNbWin =
                    notebookValue !== null && secondaryValue !== null && notebookValue > secondaryValue;
                  const isCkWin =
                    notebookValue !== null && secondaryValue !== null && secondaryValue > notebookValue;
                  return (
                    <tr
                      key={row.date}
                      className={`border-b border-outline-variant/10 last:border-0 transition ${
                        isAverageRow ? "bg-surface-container" : "hover:bg-surface-container"
                      }`}
                    >
                      <td className="py-3 px-4 font-headline font-medium text-on-surface">
                        {isAverageRow ? "Average" : formatCompactDateLabel(row.date)}
                      </td>
                      <td className="py-3 px-4 text-on-surface-variant truncate max-w-[200px]">{row.venueName}</td>
                      <td className="py-3 px-4 text-on-surface-variant truncate max-w-[140px]">
                        {isAverageRow ? "" : (buildLocationLabel([row.city, row.state]) || "—")}
                      </td>
                      <td className={`py-3 px-4 text-center ${isNbWin ? "bg-primary/5" : ""}`}>
                        <span className={`font-bold tabular-nums ${isNbWin ? "text-primary" : "text-on-surface"}`}>{formatPercent(notebookValue)}</span>
                      </td>
                      <td className={`py-3 px-4 text-center ${isCkWin ? "bg-tertiary/5" : ""}`}>
                        <span className={`font-bold tabular-nums ${isCkWin ? "text-tertiary" : "text-on-surface"}`}>{formatPercent(secondaryValue)}</span>
                      </td>
                      <td className="py-3 px-4 text-right font-label text-[10px] uppercase tracking-wider font-bold">
                        {isNbWin ? <span className="text-primary tracking-[0.24em] uppercase">{modelASlug}</span> : isCkWin ? <span className="text-tertiary tracking-[0.24em] uppercase">{modelBSlug}</span> : <span className="text-on-surface-variant">Tie</span>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}

    </div>
  );
}
