import type { Metadata } from "next";
import { CompareMetricSelect } from "@/components/compare-metric-select";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";
import { getBands, bandEntryBySlug, resolveBandSelection, getRecentAccuracy } from "@/lib/data";
import { ACTIVE_MODELS, MODEL_CONFIG, type ModelSlug } from "@/lib/config";
import { formatCompactDateLabel, formatPercent } from "@/lib/format";

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

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;

  const modelA = params.modelA ?? ACTIVE_MODELS[0] ?? "notebook";
  const modelB = params.modelB ?? ACTIVE_MODELS[1] ?? ACTIVE_MODELS[0] ?? "ckplus";
  const labelA = MODEL_CONFIG[modelA as ModelSlug]?.displayName ?? "Model A";
  const labelB = MODEL_CONFIG[modelB as ModelSlug]?.displayName ?? "Model B";

  return {
    title: `${bandName} Model Compare | JamBandNerd`,
    description: `Compare ${labelA} vs ${labelB} across the last ${COMPARISON_WINDOW} scored shows for ${bandName}.`,
  };
}

function getWinnerLabel(
  row: {
    nb10: number | null;
    ck10: number | null;
  },
  labelA: string,
  labelB: string,
) {
  if (row.nb10 === null || row.ck10 === null) {
    return "No winner";
  }

  if (row.nb10 > row.ck10) {
    return `${labelA} edge`;
  }

  if (row.ck10 > row.nb10) {
    return `${labelB} edge`;
  }

  return "Tie";
}

function averageMetric(values: Array<number | null>) {
  const presentValues = values.filter((value): value is number => value !== null);
  if (presentValues.length === 0) {
    return null;
  }

  return presentValues.reduce((sum, value) => sum + value, 0) / presentValues.length;
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

function getSelectedPrecision(
  row: {
    nbPrec10: number | null;
    nbPrec25: number | null;
    nbPrec50: number | null;
    ckPrec10: number | null;
    ckPrec25: number | null;
    ckPrec50: number | null;
  },
  model: "nb" | "ck",
  metric: ComparisonMetric,
) {
  if (model === "nb") {
    return metric === 10 ? row.nbPrec10 : metric === 25 ? row.nbPrec25 : row.nbPrec50;
  }

  return metric === 10 ? row.ckPrec10 : metric === 25 ? row.ckPrec25 : row.ckPrec50;
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

  const [notebookPerf, ckplusPerf] = await Promise.all([
    getRecentAccuracy(selectedBand, modelASlug, COMPARISON_WINDOW),
    getRecentAccuracy(selectedBand, modelBSlug, COMPARISON_WINDOW),
  ]);

  if (notebookPerf.status === "missing_env" || ckplusPerf.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the comparison route."
      />
    );
  }

  if (notebookPerf.status !== "ready" || ckplusPerf.status !== "ready") {
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
  const ckRows = ckplusPerf.status === "ready" ? ckplusPerf.rows : [];
  
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
    const ckplusValue = getSelectedMetric(r, "ck", comparisonMetric);
    if (notebookValue === null || ckplusValue === null) {
      return;
    }

    if (notebookValue > ckplusValue) nbWins++;
    else if (ckplusValue > notebookValue) ckWins++;
    else ties++;
  });

  const mobileHeadToHeadRows = headToHeadRows.slice(0, 5);
  const averageHeadToHeadRow =
    headToHeadRows.length > 0
      ? {
          date: "average",
          venueName: "",
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
        compareHref={null}
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

      <section className="grid gap-4 md:grid-cols-3">
        <div className="editorial-panel p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">{labelA} Wins</p>
          <p className="mt-3 font-headline text-4xl font-bold text-primary">{nbWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-{comparisonMetric} accuracy match-ups</p>
        </div>
        <div className="editorial-panel p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">{labelB} Wins</p>
          <p className="mt-3 font-headline text-4xl font-bold text-tertiary">{ckWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-{comparisonMetric} accuracy match-ups</p>
        </div>
        <div className="editorial-panel p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">Ties</p>
          <p className="mt-3 font-headline text-4xl font-bold text-on-surface">{ties}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Identical Top-{comparisonMetric} recall</p>
        </div>
      </section>

      {headToHeadRows.length > 0 && (
        <SectionCard
          title="Historical Performance"
          headerAccessory={
            <CompareMetricSelect
              selectedMetric={comparisonMetric}
              options={[...COMPARISON_METRIC_OPTIONS]}
            />
          }
        >
          <div className="space-y-4 md:hidden">
            {mobileHeadToHeadRows.map((row) => (
              <div
                key={row.date}
                className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low px-4 py-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-headline text-lg font-semibold text-on-surface">
                      {formatCompactDateLabel(row.date)}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-on-surface-variant">
                      {row.venueName}
                    </p>
                  </div>
                  <span className="rounded-full border border-outline-variant/20 bg-surface/70 px-2.5 py-1 font-label text-[10px] uppercase tracking-[0.16em] text-on-surface-variant">
                    {getWinnerLabel(
                      {
                        nb10: getSelectedMetric(row, "nb", comparisonMetric),
                        ck10: getSelectedMetric(row, "ck", comparisonMetric),
                      },
                      labelA,
                      labelB,
                    )}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl bg-surface/70 px-3 py-3">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                      {labelA}
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-primary">
                      {formatPercent(getSelectedMetric(row, "nb", comparisonMetric))}
                    </p>
                    <p className="mt-1 text-[11px] text-on-surface-variant">
                      Precision {formatPercent(getSelectedPrecision(row, "nb", comparisonMetric))}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-surface/70 px-3 py-3">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                      {labelB}
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-tertiary">
                      {formatPercent(getSelectedMetric(row, "ck", comparisonMetric))}
                    </p>
                    <p className="mt-1 text-[11px] text-on-surface-variant">
                      Precision {formatPercent(getSelectedPrecision(row, "ck", comparisonMetric))}
                    </p>
                  </div>
                </div>
              </div>
            ))}

            <details className="rounded-[1.35rem] border border-outline-variant/20 bg-surface-container-low">
              <summary className="cursor-pointer list-none px-4 py-4 font-headline text-sm uppercase tracking-[0.12em] text-on-surface">
                Open raw ledger
              </summary>
              <div className="overflow-x-auto px-3 pb-3">
                <table className="w-full min-w-[640px] whitespace-nowrap text-left text-sm">
                  <thead>
                    <tr className="border-b border-outline-variant/20 bg-surface-container-low">
                      <th className="py-3 px-4 font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Show Date</th>
                      <th className="py-3 px-4 font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Venue</th>
                      <th className="py-3 px-4 text-center font-label uppercase tracking-wider text-primary text-[10px] font-semibold">{labelA}</th>
                      <th className="py-3 px-4 text-center font-label uppercase tracking-wider text-tertiary text-[10px] font-semibold">{labelB}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {headToHeadLedgerRows.map((row) => {
                      const isAverageRow = row.date === "average";
                      return (
                        <tr
                          key={row.date}
                          className={`border-b border-outline-variant/10 last:border-0 ${isAverageRow ? "bg-surface-container" : ""}`}
                        >
                          <td className="py-3 px-4 font-headline font-medium text-on-surface">
                            {isAverageRow ? "Average" : formatCompactDateLabel(row.date)}
                          </td>
                          <td className="py-3 px-4 text-on-surface-variant">{row.venueName}</td>
                          <td className="py-3 px-4 text-center">
                            <span className="font-bold tabular-nums text-primary">
                              {formatPercent(getSelectedMetric(row, "nb", comparisonMetric))}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-center">
                            <span className="font-bold tabular-nums text-tertiary">
                              {formatPercent(getSelectedMetric(row, "ck", comparisonMetric))}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </details>
          </div>

          <div className="hidden overflow-x-auto md:block">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead>
                <tr className="border-b border-outline-variant/20 bg-surface-container-low">
                  <th className="py-3 px-4 font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Show Date</th>
                  <th className="py-3 px-4 font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Venue</th>
                  <th className="py-3 px-4 text-center font-label uppercase tracking-wider text-primary text-[10px] font-semibold">
                    {labelA} Top {comparisonMetric}<br/><span className="text-[8px] opacity-80 tracking-normal">(Recall / Precision)</span>
                  </th>
                  <th className="py-3 px-4 text-center font-label uppercase tracking-wider text-tertiary text-[10px] font-semibold">
                    {labelB} Top {comparisonMetric}<br/><span className="text-[8px] opacity-80 tracking-normal">(Recall / Precision)</span>
                  </th>
                  <th className="py-3 px-4 text-right font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Winner</th>
                </tr>
              </thead>
              <tbody>
                {headToHeadLedgerRows.map((row) => {
                  const isAverageRow = row.date === "average";
                  const notebookValue = getSelectedMetric(row, "nb", comparisonMetric);
                  const ckplusValue = getSelectedMetric(row, "ck", comparisonMetric);
                  const notebookPrecision = getSelectedPrecision(row, "nb", comparisonMetric);
                  const ckplusPrecision = getSelectedPrecision(row, "ck", comparisonMetric);
                  const isNbWin =
                    notebookValue !== null && ckplusValue !== null && notebookValue > ckplusValue;
                  const isCkWin =
                    notebookValue !== null && ckplusValue !== null && ckplusValue > notebookValue;
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
                      <td className={`py-3 px-4 text-center ${isNbWin ? "bg-primary/5" : ""}`}>
                        <div className="flex flex-col items-center leading-tight">
                          <span className={`font-bold tabular-nums ${isNbWin ? "text-primary" : "text-on-surface"}`}>{formatPercent(notebookValue)}</span>
                          <span className={`text-[10px] font-medium tabular-nums ${isNbWin ? "text-primary/70" : "text-on-surface-variant"}`}>{formatPercent(notebookPrecision)}</span>
                        </div>
                      </td>
                      <td className={`py-3 px-4 text-center ${isCkWin ? "bg-tertiary/5" : ""}`}>
                        <div className="flex flex-col items-center leading-tight">
                          <span className={`font-bold tabular-nums ${isCkWin ? "text-tertiary" : "text-on-surface"}`}>{formatPercent(ckplusValue)}</span>
                          <span className={`text-[10px] font-medium tabular-nums ${isCkWin ? "text-tertiary/70" : "text-on-surface-variant"}`}>{formatPercent(ckplusPrecision)}</span>
                        </div>
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
