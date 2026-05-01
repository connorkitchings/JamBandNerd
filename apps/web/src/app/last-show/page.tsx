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
import { normalizeSongName } from "@/lib/song-board";

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
    description: `View the setlist from the most recent ${bandName} show and compare it to the Notebook prediction snapshot.`,
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
  const [showState, replayState] = await Promise.all([
    getShowDetailsByDate(state.band, showDate),
    getPredictionsForDate(state.band, "notebook", showDate),
  ]);
  const show = showState.status === "ready" ? showState.show : null;
  const venue = show?.venueName ?? "Venue unavailable";
  const locationLabel = buildLocationLabel([
    show?.city ?? null,
    show?.state ?? show?.country ?? null,
  ]);
  const replayRows = replayState.status === "ready" ? replayState.snapshot.predictions : [];
  const actualSongs = new Set(
    state.setlist.songs.map((song) => normalizeSongName(song.songName)),
  );
  const replayHits = replayRows
    .slice(0, 10)
    .filter((row) => actualSongs.has(normalizeSongName(row.songName)));

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <FilterLinks pathname="/last-show" band={state.band} bands={bands} />

      <PageHero
        kicker="After the show"
        eyebrow="Last completed set"
        title={venue}
        meta={`${formatDateLabel(showDate)}${locationLabel ? ` • ${locationLabel}` : ""}`}
        description="Use this page as the bridge between the live dashboard and the historical analysis. It anchors the latest finished setlist, then replays the notebook snapshot for the same night when history exists."
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
                Replay hits
              </p>
              <p className="mt-3 font-headline text-2xl font-semibold text-primary">
                {replayState.status === "ready"
                  ? `${replayHits.length}/${Math.min(10, replayRows.length || 10)}`
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
              href={`/replay?band=${state.band}&date=${showDate}`}
              className="block rounded-xl border border-outline-variant/20 bg-surface-container-low p-4 transition hover:border-primary"
            >
              <p className="font-headline text-lg font-medium text-on-surface">
                Open Prediction Replay
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                Open both retained model boards for this exact show date.
              </p>
            </Link>
            <Link
              href={`/predictions?band=${state.band}&model=notebook`}
              className="block rounded-xl border border-outline-variant/20 bg-surface-container-low p-4 transition hover:border-primary"
            >
              <p className="font-headline text-lg font-medium text-on-surface">
                Return to live predictions
              </p>
              <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                Compare the latest public board to the most recent completed show.
              </p>
            </Link>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Prediction Replay" eyebrow="Notebook snapshot">
        {replayState.status === "ready" ? (
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Snapshot date
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  {formatDateLabel(replayState.snapshot.referenceDate)}
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Hits
                </p>
                <p className="mt-2 text-sm text-on-surface">
                  {replayHits.length} of the top 10 landed in the actual setlist
                </p>
              </div>
              <div className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4">
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                  Band
                </p>
                <p className="mt-2 text-sm text-on-surface">{bandName}</p>
              </div>
            </div>
            <SongBoard rows={replayRows} highlightSongs={actualSongs} compact />
          </div>
        ) : (
          <DataState
            title="No replay snapshot available"
            body="A completed show was found, but there was no notebook prediction snapshot stored for the same date."
          />
        )}
      </SectionCard>
    </div>
  );
}
