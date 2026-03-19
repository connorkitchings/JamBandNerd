import Link from "next/link";

import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { PredictionTable } from "@/components/prediction-table";
import { SectionCard } from "@/components/section-card";
import { SetlistTable } from "@/components/setlist-table";
import { BAND_CONFIG, MODEL_CONFIG } from "@/lib/config";
import { getExplorerSnapshot, getShowDetailsByDate } from "@/lib/data";
import {
  buildLocationLabel,
  formatCompactDateLabel,
  formatDateLabel,
  formatTimestampLabel,
} from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
    date?: string;
  }>;
};

function normalizeSongName(value: string) {
  return value.trim().toLowerCase();
}

export default async function ExplorerPage({ searchParams }: Props) {
  const params = await searchParams;
  const state = await getExplorerSnapshot(params.band, params.model, params.date);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_KEY to enable the historical explorer route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Explorer query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No historical prediction dates"
        body="No prediction history was found for the selected band/model pair."
      />
    );
  }

  const showState = await getShowDetailsByDate(state.band, state.explorer.selectedDate);
  const show = showState.status === "ready" ? showState.show : null;
  const predictions = state.explorer.predictions?.predictions ?? [];
  const setlistSongs = state.explorer.setlist?.songs ?? [];
  const actualSongs = new Set(setlistSongs.map((song) => normalizeSongName(song.songName)));
  const matchedPredictions = predictions
    .slice(0, 10)
    .filter((row) => actualSongs.has(normalizeSongName(row.songName)));
  const bustOutCandidates = predictions.filter((row) => (row.currentGap ?? 0) >= 20).slice(0, 3);
  const topPrediction = predictions[0] ?? null;
  const snapshotLabel = formatTimestampLabel(state.explorer.predictions?.predictedAt ?? null);
  const dateLabel = formatDateLabel(state.explorer.selectedDate);
  const locationLabel = buildLocationLabel([
    show?.city ?? null,
    show?.state ?? show?.country ?? null,
  ]);
  const showLabel =
    show?.venueName ?? `${BAND_CONFIG[state.band].displayName} archive replay`;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="Historical Explorer" eyebrow="Archive Navigator">
        <FilterLinks
          pathname="/explorer"
          band={state.band}
          model={state.model}
          date={state.explorer.selectedDate}
        />
      </SectionCard>

      <section className="relative overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-container p-8 md:p-10">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-gradient-to-l from-primary-container/15 to-transparent lg:block" />
        <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1.6fr)_minmax(280px,0.9fr)]">
          <div>
            <p className="font-label text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
              Historical replay
            </p>
            <h1 className="mt-3 font-headline text-4xl font-semibold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
              {showLabel}
            </h1>
            <p className="mt-3 font-headline text-base uppercase tracking-[0.08em] text-primary">
              {dateLabel}
              {locationLabel ? ` • ${locationLabel}` : ""}
            </p>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-on-surface-variant">
              Rewind a published prediction snapshot and line it up against the actual setlist for
              the selected show date. This is the main archive workflow for understanding where each
              model was early, late, or exactly right.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-xl border border-primary/20 bg-surface-container-low p-5">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Top prediction
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-on-surface">
                {topPrediction?.songName ?? "No songs"}
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">
                {topPrediction?.currentGap ?? "—"} show gap • snapshot {snapshotLabel}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/30 bg-surface-container-low p-5">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Hit rate
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-primary">
                {matchedPredictions.length}/{Math.min(10, predictions.length || 10)}
              </p>
              <p className="mt-2 text-sm text-on-surface-variant">
                Top-10 calls found in the actual setlist
              </p>
            </div>
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
        <SectionCard title="Prediction Replay" eyebrow={state.explorer.selectedDate ?? "No date"}>
          <div className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Snapshot
                </p>
                <p className="mt-2 text-sm text-on-surface">{snapshotLabel}</p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Selected model
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  {MODEL_CONFIG[state.model].displayName}
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Setlist rows
                </p>
                <p className="mt-2 text-sm text-on-surface">{setlistSongs.length}</p>
              </div>
            </div>

            <PredictionTable rows={predictions} mode={state.model} />
          </div>
        </SectionCard>

        <SectionCard title="Archive Date Rail" eyebrow={`${state.explorer.availableDates.length} snapshots`}>
          <div className="space-y-4">
            <p className="text-sm leading-6 text-on-surface-variant">
              Pick a prediction date to keep the expected songs and the actual setlist locked to the
              same show. Latest snapshots stay at the top.
            </p>
            <div className="max-h-[420px] overflow-y-auto rounded-xl border border-outline-variant/20 bg-surface-container-low p-3">
              <div className="flex flex-wrap gap-2">
                {state.explorer.availableDates.map((date) => (
                  <Link
                    key={date}
                    href={`/explorer?band=${state.band}&model=${state.model}&date=${date}`}
                    className={`rounded-full border px-3 py-1.5 font-headline text-xs uppercase tracking-[0.14rem] transition ${
                      date === state.explorer.selectedDate
                        ? "border-primary bg-primary-container text-white"
                        : "border-outline-variant bg-surface text-on-surface-variant hover:border-primary hover:text-on-surface"
                    }`}
                  >
                    {formatCompactDateLabel(date)}
                  </Link>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Replay read
              </p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                {bustOutCandidates.length > 0
                  ? `Bust-out watch: ${bustOutCandidates.map((row) => row.songName).join(", ")}`
                  : "This snapshot reads like a rotation show rather than a deep bust-out night."}
              </p>
            </div>
          </div>
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard title="Actual Setlist" eyebrow={state.explorer.selectedDate ?? "No date"}>
          {state.explorer.setlist ? (
            <div className="space-y-5">
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Result
                </p>
                <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                  {matchedPredictions.length > 0
                    ? `${matchedPredictions
                        .slice(0, 4)
                        .map((row) => row.songName)
                        .join(", ")} landed in the actual setlist.`
                    : "No Top-10 prediction match was found in this setlist."}
                </p>
              </div>
              <SetlistTable songs={state.explorer.setlist.songs} />
            </div>
          ) : (
            <DataState
              title="No setlist found"
              body="A prediction date was available, but the matching setlist payload was not found yet."
            />
          )}
        </SectionCard>

        <SectionCard title="Replay Notes" eyebrow="What changed">
          <div className="space-y-4">
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Current read
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                {MODEL_CONFIG[state.model].explanation}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Best call
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                {matchedPredictions[0]
                  ? `${matchedPredictions[0].songName} was both forecast and played.`
                  : "No direct hit surfaced in the top current prediction slice."}
              </p>
            </div>
            <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Coverage
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                {predictions.length} predicted songs available for replay across{" "}
                {state.explorer.availableDates.length} archived snapshots.
              </p>
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
