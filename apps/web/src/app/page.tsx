import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

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
  }>;
};

type BandOverview = {
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
  accuracyRows: number;
  top25Average: number | null;
};

export const metadata: Metadata = {
  title: "JamBandNerd | Active Band Dashboard",
  description:
    "Band-first setlist prediction dashboards with one active model per band, recent performance, and latest show context.",
};

function average(values: Array<number | null>) {
  const filtered = values.filter((value): value is number => value !== null);
  if (filtered.length === 0) {
    return null;
  }

  return filtered.reduce((sum, value) => sum + value, 0) / filtered.length;
}

function statusLabel(status: string) {
  if (status === "ready") {
    return "Ready";
  }
  if (status === "empty") {
    return "No board";
  }
  if (status === "missing_env") {
    return "Needs env";
  }
  return "Check";
}

export default async function HomePage({ searchParams }: Props) {
  const params = await searchParams;

  if (params.band) {
    redirect(`/predictions?band=${params.band}`);
  }

  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const summaries: BandOverview[] =
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
                snapshot?.predictions.slice(0, 3).map((row) => ({
                  rank: row.rank,
                  songName: row.songName,
                  currentGap: row.currentGap,
                })) ?? [],
              accuracyRows: accuracyRows.length,
              top25Average: average(accuracyRows.map((row) => row.recall25)),
            };
          }),
        )
      : [];
  const readyBoards = summaries.filter((summary) => summary.boardStatus === "Ready");
  const completeAccuracyWindows = summaries.filter(
    (summary) => summary.accuracyRows === 50,
  );
  const defaultBand = summaries[0]?.slug ?? "goose";

  return (
    <div className="mx-auto max-w-6xl space-y-7 pb-0">
      <section className="editorial-hero px-5 py-6 md:px-10 md:py-10">
        <div className="relative grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)] lg:items-end">
          <div>
            <span className="editorial-kicker">JamBandNerd</span>
            <h1 className="mt-3 max-w-4xl font-headline text-3xl font-bold uppercase tracking-[-0.05em] text-on-surface md:text-6xl">
              Active band overview
            </h1>
            <p className="mt-4 max-w-3xl text-sm leading-6 text-on-surface-variant md:text-[0.95rem] md:leading-7">
              One active prediction model per band, with each public route
              centered on the selected band&apos;s board, recent scoring window,
              and latest show context.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="editorial-panel px-4 py-4 text-center">
              <p className="font-headline text-2xl font-semibold text-on-surface">
                {bands.length || "—"}
              </p>
              <p className="mt-1 font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
                Active bands
              </p>
            </div>
            <div className="editorial-panel px-4 py-4 text-center">
              <p className="font-headline text-2xl font-semibold text-on-surface">
                {readyBoards.length || "—"}
              </p>
              <p className="mt-1 font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
                Boards ready
              </p>
            </div>
            <div className="editorial-panel px-4 py-4 text-center">
              <p className="font-headline text-2xl font-semibold text-on-surface">
                {completeAccuracyWindows.length || "—"}
              </p>
              <p className="mt-1 font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
                50-show ledgers
              </p>
            </div>
          </div>
        </div>
      </section>

      {bandsResult.status !== "ready" ? (
        <section className="editorial-panel p-6 md:p-7">
          <p className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
            Data status
          </p>
          <h2 className="mt-2 font-headline text-[1.35rem] font-semibold uppercase tracking-[-0.03em] text-on-surface">
            Active bands unavailable
          </h2>
          <p className="mt-4 text-sm leading-6 text-on-surface-variant">
            {bandsResult.status === "missing_env"
              ? "Set SUPABASE_URL and SUPABASE_ANON_KEY to load the active band registry."
              : bandsResult.status === "error"
                ? bandsResult.message
                : "No active bands were returned from the bands table."}
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/predictions"
              className="rounded-full border border-outline-variant/35 bg-surface/70 px-5 py-2.5 font-headline text-xs font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
            >
              Predictions
            </Link>
            <Link
              href="/performance"
              className="rounded-full border border-outline-variant/35 bg-surface/70 px-5 py-2.5 font-headline text-xs font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
            >
              Performance
            </Link>
          </div>
        </section>
      ) : null}

      {summaries.length > 0 ? (
        <section className="space-y-4">
          <div className="flex flex-col gap-2 px-1 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
                Band dashboards
              </p>
              <h2 className="mt-2 font-headline text-[1.35rem] font-semibold uppercase tracking-[-0.03em] text-on-surface">
                Select a band
              </h2>
            </div>
            <Link
              href={`/predictions?band=${defaultBand}`}
              className="w-fit rounded-full border border-outline-variant/35 bg-surface/70 px-5 py-2.5 font-headline text-xs font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:text-primary"
            >
              Open default board
            </Link>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {summaries.map((summary) => (
              <article
                key={summary.slug}
                className="editorial-panel flex min-h-[21rem] flex-col p-5"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
                      {summary.boardStatus}
                    </p>
                    <h3 className="mt-2 font-headline text-2xl font-semibold text-on-surface">
                      {summary.displayName}
                    </h3>
                  </div>
                  <span className="rounded-full border border-outline-variant/25 bg-surface-container-low px-3 py-1 font-mono text-xs uppercase text-on-surface-variant">
                    {summary.slug}
                  </span>
                </div>

                <div className="mt-5 border-t border-outline-variant/15 pt-4">
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                    Next target
                  </p>
                  <p className="mt-2 font-headline text-lg font-semibold text-on-surface">
                    {formatDateLabel(summary.nextShowDate)}
                  </p>
                  <p className="mt-1 text-sm text-on-surface-variant">
                    {summary.nextShowVenue ?? "Venue unavailable"}
                    {summary.nextShowLocation ? ` • ${summary.nextShowLocation}` : ""}
                  </p>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-3">
                  <div className="rounded-lg bg-surface-container-low px-3 py-3">
                    <p className="font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
                      Last 50 top 25
                    </p>
                    <p className="mt-1 font-headline text-lg font-semibold text-on-surface">
                      {formatPercent(summary.top25Average)}
                    </p>
                  </div>
                  <div className="rounded-lg bg-surface-container-low px-3 py-3">
                    <p className="font-label text-[9px] uppercase tracking-[0.16em] text-on-surface-variant">
                      Scored shows
                    </p>
                    <p className="mt-1 font-headline text-lg font-semibold text-on-surface">
                      {summary.accuracyRows || "—"}
                    </p>
                  </div>
                </div>

                <div className="mt-5 flex-1">
                  <p className="font-label text-[10px] uppercase tracking-[0.18em] text-on-surface-variant">
                    Top board picks
                  </p>
                  {summary.topSongs.length > 0 ? (
                    <div className="mt-3 space-y-2">
                      {summary.topSongs.map((song) => (
                        <div
                          key={`${summary.slug}-${song.rank}-${song.songName}`}
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
                  ) : (
                    <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                      No current prediction rows are available for this band.
                    </p>
                  )}
                </div>

                <div className="mt-5 grid grid-cols-3 gap-2">
                  <Link
                    href={`/predictions?band=${summary.slug}`}
                    className="rounded-lg border border-outline-variant/25 bg-surface-container-low px-2 py-2 text-center font-headline text-[10px] font-semibold uppercase tracking-[0.12em] text-on-surface transition hover:border-primary hover:text-primary"
                  >
                    Predict
                  </Link>
                  <Link
                    href={`/performance?band=${summary.slug}`}
                    className="rounded-lg border border-outline-variant/25 bg-surface-container-low px-2 py-2 text-center font-headline text-[10px] font-semibold uppercase tracking-[0.12em] text-on-surface transition hover:border-primary hover:text-primary"
                  >
                    Stats
                  </Link>
                  <Link
                    href={`/last-show?band=${summary.slug}`}
                    className="rounded-lg border border-outline-variant/25 bg-surface-container-low px-2 py-2 text-center font-headline text-[10px] font-semibold uppercase tracking-[0.12em] text-on-surface transition hover:border-primary hover:text-primary"
                  >
                    Last
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
