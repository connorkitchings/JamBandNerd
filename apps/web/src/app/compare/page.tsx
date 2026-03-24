import type { Metadata } from "next";
import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
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

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <FilterLinks pathname="/compare" band={notebook.band} bands={bands} />

      <section className="relative overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-container px-6 py-6 shadow-[0_24px_80px_rgba(0,0,0,0.08)] md:px-10 md:py-8">
        <div className="absolute inset-y-0 left-0 hidden w-1/3 bg-gradient-to-r from-tertiary/5 to-transparent lg:block" />
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-gradient-to-l from-primary-container/15 to-transparent lg:block" />
        <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
          <div>
            <p className="font-label text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
              Model divergence
            </p>
            <h1 className="mt-3 font-headline text-4xl font-semibold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
              {bandName} comparison board
            </h1>
            <p className="mt-3 font-headline text-base uppercase tracking-[0.08em] text-primary">
              {show?.venueName ?? "Latest prediction snapshot"}
              {locationLabel ? ` • ${locationLabel}` : ""}
            </p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-on-surface-variant">
              Track the historical head-to-head performance exactly mapping {labelA} vs. {labelB} recall across past shows. 
              Read both latest model snapshots side-by-side to look at where they dynamically converge and diverge for the next gig.
            </p>
          </div>
          <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
              Snapshot sync
            </p>
            <p className="mt-3 font-headline text-2xl font-semibold text-on-surface">
              {formatDateLabel(referenceDate)}
            </p>
            <p className="mt-2 text-sm leading-6 text-on-surface-variant">{syncLabel}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-primary/20 bg-surface-container-low p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">{labelA} Wins</p>
          <p className="mt-3 font-headline text-4xl font-bold text-primary">{nbWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-10 accuracy match-ups</p>
        </div>
        <div className="rounded-xl border border-tertiary/20 bg-surface-container-low p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">{labelB} Wins</p>
          <p className="mt-3 font-headline text-4xl font-bold text-tertiary">{ckWins}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Top-10 accuracy match-ups</p>
        </div>
        <div className="rounded-xl border border-outline-variant/30 bg-surface-container-low p-6 text-center">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">Ties</p>
          <p className="mt-3 font-headline text-4xl font-bold text-on-surface">{ties}</p>
          <p className="mt-1 text-[10px] font-medium text-on-surface-variant">Identical Top-10 recall</p>
        </div>
      </section>

      {headToHeadRows.length > 0 && (
        <SectionCard title="Head-to-Head Record" eyebrow={`Last ${headToHeadRows.length} shows evaluated`}>
          <div className="overflow-x-auto">
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
                {headToHeadRows.slice(0, 15).map((row) => {
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

      <section className="grid gap-4 md:grid-cols-3 pt-6 border-t border-outline-variant/20 mt-8">
        <SectionCard title={`${sharedSongs.length}/10`} eyebrow="Upcoming overlap">
          <p className="text-sm leading-6 text-on-surface-variant">
            Shared songs across both current top-10 lists.
          </p>
        </SectionCard>
        <SectionCard title={String(notebookOnly.length)} eyebrow={`${labelA} only`}>
          <p className="text-sm leading-6 text-on-surface-variant">
            Songs unique to the {labelA} model’s current top slice.
          </p>
        </SectionCard>
        <SectionCard title={String(ckplusOnly.length)} eyebrow={`${labelB} only`}>
          <p className="text-sm leading-6 text-on-surface-variant">
            Songs unique to the {labelB} model’s current top slice.
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
          <SongBoard rows={notebook.snapshot.predictions} compact modelSlug={modelASlug} secondarySongs={ckplusSongsSet} />
        </SectionCard>
        <SectionCard title={labelB} eyebrow={ckplus.snapshot.referenceDate ?? "No date"}>
          <SongBoard rows={ckplus.snapshot.predictions} compact modelSlug={modelBSlug} secondarySongs={notebookSongsSet} />
        </SectionCard>
      </div>
    </div>
  );
}
