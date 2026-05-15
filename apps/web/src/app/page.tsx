import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { DataState } from "@/components/data-state";
import { SectionCard } from "@/components/section-card";
import {
  getBands,
  getLatestPredictions,
  getNextShowDetails,
  getRecentAccuracy,
} from "@/lib/data";
import { buildLocationLabel, formatDateLabel, formatPercent } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
    teaser?: string;
  }>;
};

export const metadata: Metadata = {
  title: "JamBandNerd | Setlist Predictions",
  description:
    "Setlist predictions for the next show, with performance tracking and historical replay for supported jam bands.",
};

function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value !== null);
  if (filtered.length === 0) {
    return null;
  }
  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}

type BandTease = {
  slug: string;
  displayName: string;
  boardStatus: string;
  nextShowDate: string | null;
  nextShowVenue: string | null;
  nextShowLocation: string | null;
  topSongs: Array<{
    rank: number;
    songName: string;
    currentGap: number | null;
  }>;
  top25Average: number | null;
  accuracyRows: number;
};

function statusLabel(status: string) {
  if (status === "ready") return "Ready";
  if (status === "empty") return "No board";
  if (status === "missing_env") return "Needs env";
  return "Check";
}

export default async function HomePage({ searchParams }: Props) {
  const params = await searchParams;

  if (params.band) {
    redirect(`/predictions?band=${params.band}`);
  }

  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];

  const teases: BandTease[] =
    bands.length > 0
      ? await Promise.all(
          bands.map(async (band) => {
            const [predictionState, nextShowState, accuracyState] =
              await Promise.all([
                getLatestPredictions(band.slug),
                getNextShowDetails(band.slug),
                getRecentAccuracy(band.slug, 50),
              ]);
            const snapshot =
              predictionState.status === "ready"
                ? predictionState.snapshot
                : null;
            const nextShow =
              nextShowState.status === "ready" ? nextShowState.show : null;
            const accuracyRows =
              accuracyState.status === "ready" ? accuracyState.rows : [];

            return {
              slug: band.slug,
              displayName: band.displayName,
              boardStatus: statusLabel(predictionState.status),
              nextShowDate: nextShow?.showDate ?? snapshot?.targetShowDate ?? null,
              nextShowVenue: nextShow?.venueName ?? null,
              nextShowLocation: buildLocationLabel([
                nextShow?.city ?? null,
                nextShow?.state ?? nextShow?.country ?? null,
              ]),
              topSongs:
                snapshot?.predictions.slice(0, 5).map((row) => ({
                  rank: row.rank,
                  songName: row.songName,
                  currentGap: row.currentGap,
                })) ?? [],
              top25Average: average(accuracyRows.map((row) => row.recall25)),
              accuracyRows: accuracyRows.length,
            };
          }),
        )
      : [];

  const teaserSlug = params.teaser ?? teases[0]?.slug ?? null;
  const activeTease = teases.find((t) => t.slug === teaserSlug) ?? teases[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-0">
      <section className="editorial-hero px-6 py-8 md:px-10 md:py-14">
        <div className="relative max-w-4xl">
          <span className="editorial-kicker">JamBandNerd</span>
          <h1 className="mt-4 max-w-3xl font-headline text-4xl font-bold uppercase leading-tight tracking-[-0.05em] text-on-surface md:text-6xl lg:text-7xl">
            What are they playing next?
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-on-surface-variant">
            Setlist predictions for the next show, plus performance tracking and
            historical analysis in one place.
          </p>
          <div className="mt-8 grid gap-4 sm:max-w-xl sm:grid-cols-2">
            <Link
              href="/predictions"
              className="inline-flex min-h-12 items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary"
            >
              View Predictions
            </Link>
            <Link
              href="/performance"
              className="inline-flex min-h-12 items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary"
            >
              See Performance
            </Link>
          </div>
        </div>
      </section>

      {bandsResult.status !== "ready" ? (
        <DataState
          title="Band registry unavailable"
          body={
            bandsResult.status === "missing_env"
              ? "Set SUPABASE_URL and SUPABASE_ANON_KEY to load the supported bands."
              : bandsResult.status === "error"
                ? bandsResult.message
                : "No active bands were returned from the bands table."
          }
        />
      ) : null}

      {teases.length > 0 && (
        <section className="space-y-4">
          <div>
          <h2 className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
            Teasers
          </h2>
            <div className="mt-2 flex flex-wrap gap-2">
              {teases.map((t) => (
                <Link
                  key={t.slug}
                  href={`/?teaser=${t.slug}`}
                  className={`rounded-full px-4 py-2 font-headline text-xs font-medium uppercase tracking-[0.14rem] transition ${
                    t.slug === teaserSlug
                      ? "border border-primary/25 bg-primary/12 text-primary"
                      : "border border-outline-variant/35 bg-surface/70 text-on-surface-variant hover:border-primary/35 hover:text-on-surface"
                  }`}
                >
                  {t.displayName}
                </Link>
              ))}
            </div>
          </div>

          {activeTease && (
            <div className="grid gap-4 md:grid-cols-[minmax(0,1.2fr)_minmax(240px,0.8fr)]">
              <div className="editorial-panel p-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
                      {activeTease.boardStatus}
                    </p>
                    <h3 className="mt-1 font-headline text-2xl font-semibold text-on-surface">
                      {activeTease.displayName}
                    </h3>
                  </div>
                </div>

                <div className="mt-5 border-t border-outline-variant/15 pt-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                    Next Show
                  </p>
                  <p className="mt-2 font-headline text-lg font-semibold text-on-surface">
                    {formatDateLabel(activeTease.nextShowDate)}
                  </p>
                  <p className="text-sm text-on-surface-variant">
                    {activeTease.nextShowVenue ?? "Venue unavailable"}
                    {activeTease.nextShowLocation ? ` • ${activeTease.nextShowLocation}` : ""}
                  </p>
                </div>

                {activeTease.topSongs.length > 0 && (
                  <div className="mt-5">
                    <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                      Top Picks
                    </p>
                    <div className="mt-3 space-y-2">
                      {activeTease.topSongs.map((song) => (
                        <div
                          key={`${activeTease.slug}-${song.rank}-${song.songName}`}
                          className="flex items-center justify-between gap-3 text-sm"
                        >
                          <span className="min-w-0 truncate font-headline font-medium text-on-surface">
                            {song.rank}. {song.songName}
                          </span>
                          <span className="shrink-0 rounded-full bg-surface-container-low px-2 py-0.5 font-mono text-xs text-on-surface-variant">
                            {song.currentGap ?? "-"}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 md:grid-cols-1">
                <div className="editorial-panel px-4 py-4 text-center">
                  <p className="font-headline text-2xl font-semibold text-on-surface">
                    {formatPercent(activeTease.top25Average)}
                  </p>
                  <p className="mt-1 font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
                    Last 50 Top 25
                  </p>
                </div>
                <div className="editorial-panel px-4 py-4 text-center">
                  <p className="font-headline text-2xl font-semibold text-on-surface">
                    {activeTease.accuracyRows || "—"}
                  </p>
                  <p className="mt-1 font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
                    Scored Shows
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      <section className="grid gap-4 md:grid-cols-3">
        <SectionCard
          title="Predictions"
          eyebrow="Next show"
          centered
        />
        <SectionCard
          title="Performance"
          eyebrow="Last 50 scored shows"
          centered
        />
        <SectionCard
          title="Replay"
          eyebrow="Completed shows"
          centered
        />
      </section>
    </div>
  );
}
