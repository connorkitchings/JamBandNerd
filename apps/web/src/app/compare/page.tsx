import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { SongBoard } from "@/components/song-board";
import { SectionCard } from "@/components/section-card";
import { BAND_CONFIG } from "@/lib/config";
import { getLatestPredictions, getShowDetailsByDate } from "@/lib/data";
import {
  buildLocationLabel,
  formatCompactDateLabel,
  formatDateLabel,
} from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
  }>;
};

function normalizeSongName(value: string) {
  return value.trim().toLowerCase();
}

export default async function ComparePage({ searchParams }: Props) {
  const params = await searchParams;
  const [notebook, ckplus] = await Promise.all([
    getLatestPredictions(params.band, "notebook"),
    getLatestPredictions(params.band, "ckplus"),
  ]);

  if (notebook.status === "missing_env" || ckplus.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_KEY to enable the comparison route."
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
      : `Notebook: ${formatCompactDateLabel(notebook.snapshot.referenceDate)} • CK+: ${formatCompactDateLabel(ckplus.snapshot.referenceDate)}`;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Model Compare" eyebrow="Consensus Engine">
        <FilterLinks pathname="/compare" band={notebook.band} />
      </SectionCard>

      <section className="rounded-xl border border-outline-variant/30 bg-surface-container p-8 md:p-10">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.8fr)]">
          <div>
            <p className="font-label text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
              Model divergence
            </p>
            <h1 className="mt-3 font-headline text-4xl font-semibold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
              {BAND_CONFIG[notebook.band].displayName} comparison board
            </h1>
            <p className="mt-3 font-headline text-base uppercase tracking-[0.08em] text-primary">
              {show?.venueName ?? "Latest prediction snapshot"}
              {locationLabel ? ` • ${locationLabel}` : ""}
            </p>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-on-surface-variant">
              Read both latest model snapshots side by side, then look at where they converge,
              where they split, and which songs move the most between the two rankings.
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
        <SectionCard title={`${sharedSongs.length}/10`} eyebrow="Top-10 overlap">
          <p className="text-sm leading-6 text-on-surface-variant">
            Shared songs across both current top-10 lists.
          </p>
        </SectionCard>
        <SectionCard title={String(notebookOnly.length)} eyebrow="Notebook only">
          <p className="text-sm leading-6 text-on-surface-variant">
            Songs unique to the notebook model’s current top slice.
          </p>
        </SectionCard>
        <SectionCard title={String(ckplusOnly.length)} eyebrow="CK+ only">
          <p className="text-sm leading-6 text-on-surface-variant">
            Songs unique to the CK+ model’s current top slice.
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
                  <div className="text-right text-sm text-on-surface-variant">
                    <p>N {row.notebookRank}</p>
                    <p>C {row.ckplusRank}</p>
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
                Notebook angle
              </p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                {notebookOnly.length > 0
                  ? notebookOnly.map((row) => row.songName).join(", ")
                  : "Notebook is currently aligned with CK+ across the visible top 10."}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-tertiary">
                CK+ angle
              </p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                {ckplusOnly.length > 0
                  ? ckplusOnly.map((row) => row.songName).join(", ")
                  : "CK+ is currently aligned with Notebook across the visible top 10."}
              </p>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Notebook" eyebrow={notebook.snapshot.referenceDate ?? "No date"}>
          <SongBoard rows={notebook.snapshot.predictions} compact />
        </SectionCard>
        <SectionCard title="CK+" eyebrow={ckplus.snapshot.referenceDate ?? "No date"}>
          <SongBoard rows={ckplus.snapshot.predictions} compact />
        </SectionCard>
      </div>
    </div>
  );
}
