import type { Metadata } from "next";
import Link from "next/link";

import { DataState } from "@/components/data-state";
import { FilterLinks } from "@/components/filter-links";
import { PageHero } from "@/components/page-hero";
import {
  ResponsiveTableFrame,
  TABLE_CELL_CLASS,
  TABLE_HEAD_CLASS,
} from "@/components/responsive-table";
import { SectionCard } from "@/components/section-card";
import {
  bandEntryBySlug,
  getBands,
  getVenueAnalytics,
  resolveBandSelection,
} from "@/lib/data";
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
    venue?: string;
  }>;
};

function buildVenueHref(band: string, venueKey: string) {
  const params = new URLSearchParams();
  params.set("band", band);
  params.set("venue", venueKey);
  return `/venues?${params.toString()}`;
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const params = await searchParams;
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const bandSelection = resolveBandSelection(bands, params.band);
  const bandName = bandSelection.bandEntry?.displayName ?? bandSelection.requestedSlug;

  return {
    title: `${bandName} Venue Analytics | JamBandNerd`,
    description: `Explore venue-specific song history and repeat patterns for ${bandName}.`,
  };
}

export default async function VenueAnalyticsPage({ searchParams }: Props) {
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
  const state = await getVenueAnalytics(selectedBand, params.venue);

  if (state.status === "missing_env") {
    return (
      <DataState
        title="Supabase environment required"
        body="Set SUPABASE_URL and SUPABASE_ANON_KEY to enable the venue analytics route."
      />
    );
  }

  if (state.status === "error") {
    return <DataState title="Venue analytics query failed" body={state.message} />;
  }

  if (state.status === "empty") {
    return (
      <DataState
        title="No venue history available"
        body="No historical venue rows with usable show metadata were found for the selected band."
      />
    );
  }

  const bandEntry = bandEntryBySlug(bands, state.band);
  const bandName = bandEntry?.displayName ?? state.band;
  const snapshot = state.snapshot;
  const locationLabel = snapshot
    ? buildLocationLabel([snapshot.city, snapshot.region])
    : null;
  const fallbackVenue = state.venues[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <FilterLinks pathname="/venues" band={state.band} bands={bands} />

      <PageHero
        kicker="Room history"
        eyebrow="Venue-specific patterns"
        title={snapshot?.venueName ?? "Venue Analytics"}
        meta={`${locationLabel ? `${locationLabel} • ` : ""}${bandName}`}
        description={`Read the rooms where ${bandName} tends to repeat history. This view surfaces venue frequency, common songs, and quick links back into show-level replay.`}
        aside={
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <div className="editorial-panel p-5 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Selected venue
              </p>
              <p className="mt-3 font-headline text-2xl font-bold text-on-surface">
                {snapshot ? snapshot.showCount : "—"}
              </p>
              <p className="mt-1 text-[10px] font-medium text-on-surface-variant">
                {snapshot
                  ? "historical shows with this venue key"
                  : "choose a valid venue from the rail"}
              </p>
            </div>
            <div className="editorial-panel p-5 text-center">
              <p className="font-label text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">
                Venue options
              </p>
              <p className="mt-3 font-headline text-2xl font-bold text-on-surface">
                {state.venues.length}
              </p>
              <p className="mt-1 text-[10px] font-medium text-on-surface-variant">
                ranked by historical show count
              </p>
            </div>
          </div>
        }
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.18fr)_minmax(300px,0.82fr)]">
        <div className="space-y-6">
          {snapshot ? (
            <>
              <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <SectionCard title={String(snapshot.showCount)} eyebrow="Shows">
                  <p className="text-sm leading-6 text-on-surface-variant">
                    Historical appearances at this venue identity.
                  </p>
                </SectionCard>
                <SectionCard title={String(snapshot.uniqueSongs)} eyebrow="Unique Songs">
                  <p className="text-sm leading-6 text-on-surface-variant">
                    Distinct songs captured across these venue setlists.
                  </p>
                </SectionCard>
                <SectionCard
                  title={snapshot.averageSongsPerShow.toFixed(1)}
                  eyebrow="Avg Songs / Show"
                >
                  <p className="text-sm leading-6 text-on-surface-variant">
                    Mean deduped setlist rows per show at this stop.
                  </p>
                </SectionCard>
                <SectionCard
                  title={formatCompactDateLabel(snapshot.latestShowDate)}
                  eyebrow="Latest Show"
                >
                  <p className="text-sm leading-6 text-on-surface-variant">
                    First show {formatCompactDateLabel(snapshot.firstShowDate)}.
                  </p>
                </SectionCard>
              </section>

              <SectionCard title="Top Songs At This Venue" eyebrow="Repeat history">
                <ResponsiveTableFrame
                  minWidthClassName="min-w-[640px]"
                  testId="venue-top-songs"
                >
                  <thead>
                    <tr className="border-b border-outline-variant/20 bg-surface-container-low">
                      <th className={TABLE_HEAD_CLASS}>Song</th>
                      <th className={`${TABLE_HEAD_CLASS} text-right`}>Venue Shows</th>
                      <th className={`${TABLE_HEAD_CLASS} text-right`}>Hit Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.topSongs.slice(0, 20).map((song) => (
                      <tr
                        key={song.songName}
                        className="border-b border-outline-variant/10 last:border-b-0"
                      >
                        <td className={`${TABLE_CELL_CLASS} font-headline text-on-surface`}>
                          {song.songName}
                        </td>
                        <td className={`${TABLE_CELL_CLASS} text-right text-on-surface-variant`}>
                          {song.showCount} / {snapshot.showCount}
                        </td>
                        <td
                          className={`${TABLE_CELL_CLASS} text-right font-medium tabular-nums text-primary`}
                        >
                          {formatPercent(song.percentOfShows)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </ResponsiveTableFrame>
              </SectionCard>

              <SectionCard title="Recent Shows" eyebrow="Replay these nights">
                <div className="space-y-3">
                  {snapshot.recentShows.map((show) => (
                    <Link
                      key={show.showId}
                      href={`/replay?band=${state.band}&date=${show.showDate}`}
                      className="touch-manipulation block rounded-xl border border-outline-variant/20 bg-surface-container-low p-4 transition hover:border-primary hover:bg-surface-container"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div>
                          <p className="font-headline text-lg font-medium text-on-surface">
                            {formatDateLabel(show.showDate)}
                          </p>
                          <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                            {show.songCount} logged songs for this venue replay.
                          </p>
                        </div>
                        <span className="font-label text-[10px] uppercase tracking-[0.18rem] text-primary">
                          Replay
                        </span>
                      </div>
                    </Link>
                  ))}
                </div>
              </SectionCard>
            </>
          ) : (
            <SectionCard title="Venue Selection" eyebrow="Unavailable">
              <DataState
                title="Venue not found"
                body={
                  state.selectionError && fallbackVenue
                    ? `${state.selectionError} Try ${fallbackVenue.label} instead.`
                    : state.selectionError ??
                      "Choose a venue from the rail to load analytics."
                }
              />
            </SectionCard>
          )}
        </div>

        <SectionCard
          title="Venue Rail"
          eyebrow={`${state.venues.length} available for ${bandName}`}
        >
          <div className="space-y-4">
            <p className="text-sm leading-6 text-on-surface-variant">
              Use the highest-volume rooms as a fast read on venue character, then drill
              into a specific date through Replay.
            </p>
            <div className="max-h-[720px] overflow-y-auto rounded-xl border border-outline-variant/20 bg-surface-container-low p-3">
              {state.venues.length === 0 ? (
                <p className="py-8 text-center text-sm text-on-surface-variant">
                  No venues available for this band.
                </p>
              ) : (
                <div className="space-y-2">
                  {state.venues.map((venue) => {
                    const isActive = venue.key === state.selectedVenueKey && Boolean(snapshot);
                    return (
                      <Link
                        key={venue.key}
                        href={buildVenueHref(state.band, venue.key)}
                        className={`touch-manipulation block rounded-xl border px-4 py-3 transition ${
                          isActive
                            ? "border-primary bg-primary-container/15"
                            : "border-outline-variant/20 hover:border-primary hover:bg-surface-container"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-headline text-sm font-medium uppercase tracking-[0.04rem] text-on-surface">
                              {venue.venueName}
                            </p>
                            <p className="mt-1 text-xs leading-5 text-on-surface-variant">
                              {buildLocationLabel([venue.city, venue.region]) ||
                                "Location unavailable"}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="font-headline text-base text-primary">
                              {venue.showCount}
                            </p>
                            <p className="text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                              shows
                            </p>
                          </div>
                        </div>
                        <p className="mt-3 text-[11px] uppercase tracking-[0.16rem] text-on-surface-variant">
                          latest {formatCompactDateLabel(venue.latestShowDate)}
                        </p>
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
