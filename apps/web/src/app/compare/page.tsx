import type { Metadata } from "next";
import { DashboardSideNav } from "@/components/dashboard-side-nav";
import { DataState } from "@/components/data-state";
import { PageHero } from "@/components/page-hero";
import { SongBoard } from "@/components/song-board";
import { SectionCard } from "@/components/section-card";
import { getBands, getLatestPredictions, getShowDetailsByDate, bandEntryBySlug, resolveBandSelection, getRecentAccuracy } from "@/lib/data";
import { ACTIVE_MODELS, MODEL_CONFIG, type ModelSlug } from "@/lib/config";
import {
  buildLocationLabel,
  formatCompactDateLabel,
  formatDateLabel,
  formatPercent,
} from "@/lib/format";

export const dynamic = "force-dynamic";

const HEAD_TO_HEAD_ROW_LIMIT = 15;

type Props = {
  searchParams: Promise<{
    band?: string;
    modelA?: string;
    modelB?: string;
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
    description: `Compare ${labelA} vs ${labelB} model predictions side-by-side for ${bandName}.`,
  };
}

function normalizeSongName(value: string) {
  return value.trim().toLowerCase();
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

  const labelA = MODEL_CONFIG[modelASlug].displayName;
  const labelB = MODEL_CONFIG[modelBSlug].displayName;

  const [notebook, ckplus, notebookPerf, ckplusPerf] = await Promise.all([
    getLatestPredictions(selectedBand, modelASlug),
    getLatestPredictions(selectedBand, modelBSlug),
    getRecentAccuracy(selectedBand, modelASlug, 50),
    getRecentAccuracy(selectedBand, modelBSlug, 50),
  ]);

  if (notebook.status === "missing_env" || ckplus.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the comparison route."
      />
    );
  }

  if (notebook.status !== "ready" || ckplus.status !== "ready") {
    return (
      <DataState
        title="Comparison data unavailable"
        body="Both latest model snapshots were not available for this band."
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, notebook.band);
  const bandName = bandEntry?.displayName ?? notebook.band;

  const notebookTop = notebook.snapshot.predictions.slice(0, 10);
  const ckplusTop = ckplus.snapshot.predictions.slice(0, 10);
  const notebookRanks = new Map(
    notebookTop.map((row) => [normalizeSongName(row.songName), row.rank] as const),
  );
  const ckplusRanks = new Map(
    ckplusTop.map((row) => [normalizeSongName(row.songName), row.rank] as const),
  );
  const sharedSongs = notebookTop
    .filter((row) => ckplusRanks.has(normalizeSongName(row.songName)))
    .map((row) => {
      const key = normalizeSongName(row.songName);
      return {
        songName: row.songName,
        notebookRank: row.rank,
        ckplusRank: ckplusRanks.get(key) ?? row.rank,
      };
    })
    .sort(
      (left, right) =>
        Math.abs(left.notebookRank - left.ckplusRank) -
        Math.abs(right.notebookRank - right.ckplusRank),
    );
  const notebookOnly = notebookTop.filter(
    (row) => !ckplusRanks.has(normalizeSongName(row.songName)),
  );
  const ckplusOnly = ckplusTop.filter(
    (row) => !notebookRanks.has(normalizeSongName(row.songName)),
  );
  
  const notebookSongsSet = new Set(notebookRanks.keys());
  const ckplusSongsSet = new Set(ckplusRanks.keys());

  const nbRows = notebookPerf.status === "ready" ? notebookPerf.rows : [];
  const ckRows = ckplusPerf.status === "ready" ? ckplusPerf.rows : [];
  
  const sharedDates = new Set([...nbRows.map(r => r.showDate), ...ckRows.map(r => r.showDate)]);
  const headToHeadRows = Array.from(sharedDates)
    .filter((date): date is string => date !== null)
    .map(date => {
      const nbRow = nbRows.find(r => r.showDate === date);
      const ckRow = ckRows.find(r => r.showDate === date);
      return {
        date,
        venueName: nbRow?.venueName ?? ckRow?.venueName ?? "Unknown Venue",
        nb10: nbRow?.k10Recall ?? null,
        nbPrec10: nbRow?.k10Precision ?? null,
        ck10: ckRow?.k10Recall ?? null,
        ckPrec10: ckRow?.k10Precision ?? null,
      };
    })
    .filter(r => r.nb10 !== null && r.ck10 !== null)
    .sort((a, b) => b.date.localeCompare(a.date));

  let nbWins = 0;
  let ckWins = 0;
  let ties = 0;

  headToHeadRows.forEach(r => {
    if (r.nb10! > r.ck10!) nbWins++;
    else if (r.ck10! > r.nb10!) ckWins++;
    else ties++;
  });

  const referenceDate =
    notebook.snapshot.referenceDate && ckplus.snapshot.referenceDate
      ? notebook.snapshot.referenceDate >= ckplus.snapshot.referenceDate
        ? notebook.snapshot.referenceDate
        : ckplus.snapshot.referenceDate
      : notebook.snapshot.referenceDate ?? ckplus.snapshot.referenceDate;
  const showState = await getShowDetailsByDate(notebook.band, referenceDate);
  const show = showState.status === "ready" ? showState.show : null;
  const locationLabel = buildLocationLabel([
    show?.city ?? null,
    show?.state ?? show?.country ?? null,
  ]);
  const syncLabel =
    notebook.snapshot.referenceDate === ckplus.snapshot.referenceDate
      ? "Both models are reading the same show date."
      : `${labelA}: ${formatCompactDateLabel(notebook.snapshot.referenceDate)} • ${labelB}: ${formatCompactDateLabel(ckplus.snapshot.referenceDate)}`;
  const mobileHeadToHeadRows = headToHeadRows.slice(0, 5);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <DashboardSideNav
        band={notebook.band}
        model={modelASlug}
        bands={bands}
        pathname="/compare"
        compareHref={null}
        hideSecondary
        bandLinks={bands.map((item) => ({
          href: `/compare?band=${item.slug}&modelA=${modelASlug}&modelB=${modelBSlug}`,
          label: item.displayName,
          active: item.slug === notebook.band,
        }))}
      />

      <PageHero
        kicker="Head-to-head"
        eyebrow="Model divergence"
        title={`${bandName} comparison board`}
        meta={`${show?.venueName ?? "Latest prediction snapshot"}${locationLabel ? ` • ${locationLabel}` : ""}`}
        description={`Track ${labelA} versus ${labelB} across recent scored shows, then read where the two boards currently converge and break apart for the next night.`}
        aside={
          <div className="editorial-panel p-5">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
              Snapshot sync
            </p>
            <p className="mt-3 font-headline text-2xl font-semibold text-on-surface">
              {formatDateLabel(referenceDate)}
            </p>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">{syncLabel}</p>
          </div>
        }
      />

      <section className="grid gap-4 md:grid-cols-3">
        <div className="editorial-panel p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">{labelA} Wins</p>
          <p className="mt-3 font-headline text-4xl font-bold text-primary">{nbWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-10 accuracy match-ups</p>
        </div>
        <div className="editorial-panel p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">{labelB} Wins</p>
          <p className="mt-3 font-headline text-4xl font-bold text-tertiary">{ckWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-10 accuracy match-ups</p>
        </div>
        <div className="editorial-panel p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">Ties</p>
          <p className="mt-3 font-headline text-4xl font-bold text-on-surface">{ties}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Identical Top-10 recall</p>
        </div>
      </section>

      {headToHeadRows.length > 0 && (
        <SectionCard title="Head-to-Head Record" eyebrow={`Last ${headToHeadRows.length} shows evaluated`}>
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
                    {getWinnerLabel(row, labelA, labelB)}
                  </span>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-2xl bg-surface/70 px-3 py-3">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-primary">
                      {labelA}
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-primary">
                      {formatPercent(row.nb10)}
                    </p>
                    <p className="mt-1 text-[11px] text-on-surface-variant">
                      Precision {formatPercent(row.nbPrec10)}
                    </p>
                  </div>
                  <div className="rounded-2xl bg-surface/70 px-3 py-3">
                    <p className="font-label text-[9px] uppercase tracking-[0.16rem] text-tertiary">
                      {labelB}
                    </p>
                    <p className="mt-1 font-headline text-base font-bold text-tertiary">
                      {formatPercent(row.ck10)}
                    </p>
                    <p className="mt-1 text-[11px] text-on-surface-variant">
                      Precision {formatPercent(row.ckPrec10)}
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
                    {headToHeadRows.slice(0, HEAD_TO_HEAD_ROW_LIMIT).map((row) => (
                      <tr key={row.date} className="border-b border-outline-variant/10 last:border-0">
                        <td className="py-3 px-4 font-headline font-medium text-on-surface">{formatCompactDateLabel(row.date)}</td>
                        <td className="py-3 px-4 text-on-surface-variant">{row.venueName}</td>
                        <td className="py-3 px-4 text-center">
                          <span className="font-bold tabular-nums text-primary">{formatPercent(row.nb10)}</span>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className="font-bold tabular-nums text-tertiary">{formatPercent(row.ck10)}</span>
                        </td>
                      </tr>
                    ))}
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
                    {labelA} Top 10<br/><span className="text-[8px] opacity-80 tracking-normal">(Recall / Precision)</span>
                  </th>
                  <th className="py-3 px-4 text-center font-label uppercase tracking-wider text-tertiary text-[10px] font-semibold">
                    {labelB} Top 10<br/><span className="text-[8px] opacity-80 tracking-normal">(Recall / Precision)</span>
                  </th>
                  <th className="py-3 px-4 text-right font-label uppercase tracking-wider text-on-surface-variant text-[10px] font-semibold">Winner</th>
                </tr>
              </thead>
              <tbody>
                {headToHeadRows.slice(0, HEAD_TO_HEAD_ROW_LIMIT).map((row) => {
                  const isNbWin = row.nb10! > row.ck10!;
                  const isCkWin = row.ck10! > row.nb10!;
                  return (
                    <tr key={row.date} className="border-b border-outline-variant/10 last:border-0 hover:bg-surface-container transition">
                      <td className="py-3 px-4 font-headline font-medium text-on-surface">{formatCompactDateLabel(row.date)}</td>
                      <td className="py-3 px-4 text-on-surface-variant truncate max-w-[200px]">{row.venueName}</td>
                      <td className={`py-3 px-4 text-center ${isNbWin ? "bg-primary/5" : ""}`}>
                        <div className="flex flex-col items-center leading-tight">
                          <span className={`font-bold tabular-nums ${isNbWin ? "text-primary" : "text-on-surface"}`}>{formatPercent(row.nb10)}</span>
                          <span className={`text-[10px] font-medium tabular-nums ${isNbWin ? "text-primary/70" : "text-on-surface-variant"}`}>{formatPercent(row.nbPrec10)}</span>
                        </div>
                      </td>
                      <td className={`py-3 px-4 text-center ${isCkWin ? "bg-tertiary/5" : ""}`}>
                        <div className="flex flex-col items-center leading-tight">
                          <span className={`font-bold tabular-nums ${isCkWin ? "text-tertiary" : "text-on-surface"}`}>{formatPercent(row.ck10)}</span>
                          <span className={`text-[10px] font-medium tabular-nums ${isCkWin ? "text-tertiary/70" : "text-on-surface-variant"}`}>{formatPercent(row.ckPrec10)}</span>
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

      <section className="grid gap-4 sm:grid-cols-3 pt-6 border-t border-outline-variant/20 mt-8">
        <SectionCard title={`${sharedSongs.length}/10`} eyebrow="Upcoming overlap">
          <p className="text-sm leading-6 text-on-surface-variant">
            Shared songs across both current top-10 lists.
          </p>
        </SectionCard>
        <SectionCard title={String(notebookOnly.length)} eyebrow={`${labelA} only`}>
          <p className="text-sm leading-6 text-on-surface-variant">
            Songs unique to the {labelA} model&apos;s current top slice.
          </p>
        </SectionCard>
        <SectionCard title={String(ckplusOnly.length)} eyebrow={`${labelB} only`}>
          <p className="text-sm leading-6 text-on-surface-variant">
            Songs unique to the {labelB} model&apos;s current top slice.
          </p>
        </SectionCard>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
        <SectionCard title="Consensus Board" eyebrow="Shared songs">
          {sharedSongs.length > 0 ? (
            <div className="space-y-3">
              {sharedSongs.slice(0, 6).map((row) => (
                <div
                  key={row.songName}
                  className="flex items-center justify-between rounded-xl border border-outline-variant/20 bg-surface-container-low px-4 py-3"
                >
                  <div>
                    <p className="font-headline text-lg font-medium text-on-surface">
                      {row.songName}
                    </p>
                    <p className="text-xs text-on-surface-variant">
                      Average rank {(row.notebookRank + row.ckplusRank) / 2}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <span
                      className="flex h-6 w-8 items-center justify-center rounded bg-primary/10 font-mono text-[10px] font-bold text-primary ring-1 ring-inset ring-primary/20"
                      title={`${labelA} Rank`}
                    >
                      {labelA[0].toUpperCase()}{row.notebookRank}
                    </span>
                    <span
                      className="flex h-6 w-8 items-center justify-center rounded bg-tertiary/10 font-mono text-[10px] font-bold text-tertiary ring-1 ring-inset ring-tertiary/20"
                      title={`${labelB} Rank`}
                    >
                      {labelB[0].toUpperCase()}{row.ckplusRank}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <DataState
              title="No overlap"
              body="The current model slices do not share any songs in the top 10."
            />
          )}
        </SectionCard>

        <SectionCard title="Divergence Watch" eyebrow="Unique songs">
          <div className="space-y-4">
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
                {labelA} angle
              </p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                {notebookOnly.length > 0
                  ? notebookOnly.map((row) => row.songName).join(", ")
                  : `${labelA} is currently aligned with ${labelB} across the visible top 10.`}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-tertiary">
                {labelB} angle
              </p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                {ckplusOnly.length > 0
                  ? ckplusOnly.map((row) => row.songName).join(", ")
                  : `${labelB} is currently aligned with ${labelA} across the visible top 10.`}
              </p>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title={labelA} eyebrow={notebook.snapshot.referenceDate ?? "No date"}>
          <div className="overflow-x-auto [-webkit-overflow-scrolling:touch]">
            <SongBoard rows={notebook.snapshot.predictions} compact modelSlug={modelASlug} secondarySongs={ckplusSongsSet} />
          </div>
        </SectionCard>
        <SectionCard title={labelB} eyebrow={ckplus.snapshot.referenceDate ?? "No date"}>
          <div className="overflow-x-auto [-webkit-overflow-scrolling:touch]">
            <SongBoard rows={ckplus.snapshot.predictions} compact modelSlug={modelBSlug} secondarySongs={notebookSongsSet} />
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
