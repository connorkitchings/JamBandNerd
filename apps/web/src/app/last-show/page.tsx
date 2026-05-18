import type { Metadata } from "next";
import Link from "next/link";

import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { PageHero } from "@/components/page-hero";
import { SongBoard } from "@/components/song-board";
import { SectionCard } from "@/components/section-card";
import { SetlistTable } from "@/components/setlist-table";
import {
  getBands,
  getLastShowSetlist,
  getPredictionsForDate,
  getShowDetailsByDate,
  bandEntryBySlug,
  resolveBandSelection,
} from "@/lib/data";
import { buildLocationLabel, formatDateLabel } from "@/lib/format";
import { computeTopKHits, normalizeSongName } from "@/lib/song-board-core";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
  }>;
};

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;

  return {
    title: `${bandName} Last Show Setlist | JamBandNerd`,
    description: `View the setlist from the most recent ${bandName} show and compare it to the prediction snapshot.`,
  };
}

export default async function LastShowPage({ searchParams }: Props) {
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
  const state = await getLastShowSetlist(selectedBand);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the last-show route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Last-show query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No last show available"
        body="No completed show with setlist data was found for the selected band."
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;

  const showDate =
    typeof state.setlist.showDetails?.show_date === "string"
      ? state.setlist.showDetails.show_date
      : "Unknown date";
  const [showState, predictionState] = await Promise.all([
    getShowDetailsByDate(state.band, showDate),
    getPredictionsForDate(state.band, showDate),
  ]);
  const show = showState.status === "ready" ? showState.show : null;
  const venue = show?.venueName ?? "Venue unavailable";
  const locationLabel = buildLocationLabel([
    show?.city ?? null,
    show?.state ?? show?.country ?? null,
  ]);
  const predictionRows = predictionState.status === "ready" ? predictionState.snapshot.predictions : [];
  const actualSongs = new Set(
    state.setlist.songs.map((song) => normalizeSongName(song.songName)),
  );
  const top10Hits = computeTopKHits(predictionRows, actualSongs, 10);
  const top25Hits = computeTopKHits(predictionRows, actualSongs, 25);
  const top50Hits = computeTopKHits(predictionRows, actualSongs, 50);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <FilterLinks pathname="/last-show" band={state.band} bands={bands} />

      <PageHero
        kicker="After the show"
        eyebrow="Last completed set"
        title={venue}
        meta={`${formatDateLabel(showDate)}${locationLabel ? ` • ${locationLabel}` : ""}`}
        description="The latest finished setlist anchored against the prediction snapshot for the same night, so you can see what landed and what missed."
        aside={
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <div className="editorial-panel p-5">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Songs logged
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-on-surface">
                {state.setlist.songs.length}
              </p>
            </div>
            <div className="editorial-panel p-5">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Top-10 hits
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-primary">
                {predictionState.status === "ready"
                  ? `${top10Hits}/${Math.min(10, predictionRows.length || 10)}`
                  : "—"}
              </p>
            </div>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
        <SectionCard title="Setlist" eyebrow="Completed show">
          <SetlistTable songs={state.setlist.songs} />
        </SectionCard>

        <SectionCard title="Jump Back In" eyebrow="Related routes">
          <div className="space-y-4">
            <Link
              href={`/predictions?band=${state.band}`}
              className="block rounded-xl border border-outline-variant/20 bg-surface-container-low p-4 transition hover:border-primary"
            >
              <p className="font-headline text-lg font-medium text-on-surface">
                Return to live predictions
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                Compare the latest board to the most recent completed show.
              </p>
            </Link>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Prediction Replay" eyebrow="Matched snapshot">
        {predictionState.status === "ready" ? (
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Snapshot date
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  {formatDateLabel(predictionState.snapshot.targetShowDate)}
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Hits
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  Top 10: {top10Hits}/{Math.min(10, predictionRows.length || 10)}
                  {" · "}
                  Top 25: {top25Hits}/{Math.min(25, predictionRows.length || 25)}
                  {" · "}
                  Top 50: {top50Hits}/{Math.min(50, predictionRows.length || 50)}
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Band
                </p>
                <p className="mt-2 text-sm text-on-surface">{bandName}</p>
              </div>
            </div>
            <SongBoard rows={predictionRows} highlightSongs={actualSongs} compact />
          </div>
        ) : (
          <DataState
            title="No prediction snapshot available"
            body="A completed show was found, but there was no prediction snapshot stored for the same date."
            headingLevel="h2"
          />
        )}
      </SectionCard>
    </div>
  );
}
