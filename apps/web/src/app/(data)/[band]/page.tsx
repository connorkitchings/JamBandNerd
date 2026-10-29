import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";

import { SectionCard } from "@/components/section-card";
import { bandPath } from "@/lib/band-routes";
import {
  getLatestPredictions,
  getNextShowDetails,
  getRecentMissingSetlistShows,
  getShowDetailsByDate,
  resolveBandPage,
} from "@/lib/data";
import {
  buildLocationLabel,
  formatCompactDateLabel,
  formatDateLabel,
} from "@/lib/format";
import { selectTeaserShow } from "@/lib/show-selection";
import { getDataClock } from "@/lib/show-status";

const TEASER_BANDS = [
  { slug: "phish", label: "Phish" },
  { slug: "wsp", label: "WSP" },
  { slug: "billy", label: "Billy" },
  { slug: "goose", label: "Goose" },
] as const;

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Gather the setlists",
    body: "We pull in setlist history for every band we cover — what was played, when, and where.",
  },
  {
    step: "02",
    title: "Take a guess at the next show",
    body: "We've built a model from years of setlist history for each band. It looks at rotation, gaps, and venue habits to rank the likeliest songs for the upcoming show.",
  },
  {
    step: "03",
    title: "See what actually happened",
    body: "After the show, we check the board against the real setlist so you can see what landed and what didn't.",
  },
] as const;

type Props = {
  params: Promise<{ band: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { bandEntry } = await resolveBandPage((await params).band);

  return {
    title: `${bandEntry.displayName} Setlist Predictions | JamBandNerd`,
    description: `Educated guesses about what ${bandEntry.displayName} will play next — and a look back at how those guesses held up.`,
  };
}

export default async function BandOverviewPage({ params }: Props) {
  const { band, bandEntry, bands } = await resolveBandPage((await params).band);

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-0">
      <section className="editorial-hero px-6 py-8 md:px-10 md:py-16">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,191,105,0.22),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(136,229,216,0.12),transparent_26%),linear-gradient(135deg,rgba(255,255,255,0.04),transparent_55%)]" />
        <div className="relative grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:items-center">
          <div className="flex h-full flex-col justify-center">
            <h1 className="max-w-3xl text-center font-headline text-4xl font-bold uppercase leading-tight tracking-[-0.05em] text-on-surface md:text-left md:text-6xl lg:text-7xl">
              What are they playing next?
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-on-surface-variant">
              We rank the songs each band might play at the next show. It&apos;s an educated guess — sometimes right, sometimes not — but always worth checking.
            </p>
            <div className="mt-8 hidden gap-3 sm:max-w-3xl md:grid md:grid-cols-2 md:gap-4">
              <Link
                href={bandPath(band, "predictions")}
                className="inline-flex w-full items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3.5 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
              >
                View Predictions
              </Link>
              <Link
                href={bandPath(band, "performance")}
                className="inline-flex w-full items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3.5 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
              >
                See Performance
              </Link>
            </div>
          </div>

          <div className="editorial-panel rounded-[1.9rem] p-6">
            <h2 className="mb-4 text-center font-label text-[10px] font-bold uppercase tracking-[0.24em] text-primary/80">
              First Look
            </h2>
            <div className="grid grid-cols-4 gap-2">
              {TEASER_BANDS.map((teaserBand) => {
                const isActive = teaserBand.slug === band;
                return (
                  <Link
                    key={teaserBand.slug}
                    href={bandPath(teaserBand.slug)}
                    aria-current={isActive ? "page" : undefined}
                    className={`flex items-center justify-center rounded-full border px-2.5 py-2 text-center font-headline text-[10px] font-bold uppercase tracking-[0.12rem] transition focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none ${
                      isActive
                        ? "border-primary/30 bg-primary/12 text-primary"
                        : "border-transparent bg-surface-container-low text-on-surface-variant hover:bg-outline-variant/20 hover:text-on-surface"
                    }`}
                  >
                    {teaserBand.label}
                  </Link>
                );
              })}
            </div>

            <Suspense fallback={<div aria-hidden="true" className="editorial-chip mt-5 h-64 animate-pulse rounded-[1.5rem]" />}>
              <BandTeaser band={band} bandName={bandEntry.displayName} />
            </Suspense>
          </div>
        </div>
      </section>

      {bands.length === 0 ? (
        <SectionCard title="Band registry unavailable" eyebrow="Data status">
          <p className="text-sm leading-6 text-on-surface-variant">
            We couldn&apos;t load the supported bands right now. Please try again in a few minutes.
          </p>
        </SectionCard>
      ) : null}

      <section className="grid grid-cols-2 gap-4 md:grid-cols-2">
        <div className="editorial-panel flex flex-col justify-center px-6 py-5 text-center">
          <p className="font-headline text-3xl font-bold text-on-surface">
            {bands.length || "-"}
          </p>
          <p className="mt-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant">
            Bands Tracked
          </p>
        </div>
        <div className="editorial-panel flex flex-col justify-center px-6 py-5 text-center">
          <p className="font-headline text-3xl font-bold text-on-surface">Daily</p>
          <p className="mt-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant">
            Refresh Cadence
          </p>
        </div>
      </section>

      <SectionCard title="How It Works">
        <div className="grid gap-4 md:grid-cols-3 md:gap-5">
          {HOW_IT_WORKS.map((item) => (
            <div
              key={item.step}
              className="flex flex-col items-center rounded-[1.15rem] border border-outline-variant/18 bg-surface/35 px-4 py-5 text-center transition-colors hover:border-primary/30 md:items-start md:px-5 md:py-5 md:text-left"
            >
              <div className="mb-3 font-mono text-2xl font-bold leading-none text-primary/75 md:text-xl">
                {item.step}
              </div>
              <p className="font-headline text-lg font-bold leading-tight text-on-surface md:text-base">
                {item.title}
              </p>
              <p className="mt-2 max-w-[24rem] text-sm leading-6 text-on-surface-variant md:max-w-none">
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </SectionCard>

      {bands.length > 0 && (
        <SectionCard title="Who We Follow">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {bands.map((item) => (
              <Link
                key={item.slug}
                href={bandPath(item.slug)}
                className="editorial-chip flex items-center justify-center rounded-[1.5rem] p-5 text-center transition-all hover:border-primary hover:bg-surface-container-high hover:shadow-md focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
              >
                <span className="font-headline text-lg font-bold text-on-surface transition-colors hover:text-primary">
                  {item.displayName}
                </span>
              </Link>
            ))}
          </div>
        </SectionCard>
      )}

    </div>
  );
}

/** Top picks for the band's upcoming show; request-time because show status depends on the date. */
async function BandTeaser({ band, bandName }: { band: string; bandName: string }) {
  await connection();
  const clock = getDataClock();
  const [predictionState, nextShowState] = await Promise.all([
    getLatestPredictions(band, clock.todayIso),
    getNextShowDetails(band, clock.todayIso),
  ]);
  const targetDate =
    predictionState.status === "ready" ? predictionState.snapshot.targetShowDate : null;
  const [missingShows, targetShowState] = await Promise.all([
    getRecentMissingSetlistShows(band, targetDate, clock),
    getShowDetailsByDate(band, targetDate),
  ]);
  // The songs come from the latest prediction snapshot, so the header must
  // describe that snapshot's target show, not simply the next scheduled show.
  const nextShow =
    targetDate !== null
      ? selectTeaserShow(
          targetDate,
          nextShowState.status === "ready" ? nextShowState.show : null,
          targetShowState.status === "ready" ? targetShowState.show : null,
        )
      : null;
  const songs =
    predictionState.status === "ready" ? predictionState.snapshot.predictions.slice(0, 3) : [];
  const locationLabel = buildLocationLabel([
    nextShow?.city ?? null,
    nextShow?.state ?? nextShow?.country ?? null,
  ]);

  return (
    <>
            {predictionState.status === "ready" ? (
              <>
                <div className="editorial-chip mt-5 rounded-[1.5rem] p-4 text-center">
                  <p className="mt-1.5 font-headline text-xl font-bold text-primary md:text-2xl">
                    {formatDateLabel(predictionState.snapshot.targetShowDate)}
                  </p>
                  <p className="mt-1 font-headline text-base text-on-surface">
                    {nextShow?.venueName ||
                      `${bandName} next show`}
                  </p>
                  <p className="mt-0.5 text-xs text-on-surface-variant">
                    {locationLabel || "Location unavailable"}
                  </p>
                  {missingShows.length > 0 && (
                    <p
                      role="status"
                      className="mt-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-[11px] leading-relaxed text-amber-300"
                    >
                      Awaiting upstream setlist for{" "}
                      {missingShows
                        .map((show) => formatCompactDateLabel(show.showDate))
                        .join(", ")}
                    </p>
                  )}
                </div>

                <div className="editorial-chip mt-4 rounded-[1.5rem] p-4">
                  <div className="mb-3 flex items-center justify-between border-b border-outline-variant/15 pb-2">
                    <p className="font-label text-[10px] font-medium uppercase tracking-[0.16rem] text-on-surface-variant/70">
                      Top Picks
                    </p>
                    <p className="font-label text-[10px] font-medium uppercase tracking-[0.16rem] text-on-surface-variant/70">
                      Current Gap
                    </p>
                  </div>
                  <div className="space-y-2.5">
                    {songs.map((row) => (
                      <div
                        key={`${row.rank}-${row.songName}`}
                        className="group flex items-center justify-between gap-3"
                      >
                        <div className="flex min-w-0 items-center gap-3">
                          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-container font-headline text-xs font-bold text-on-surface-variant">
                            {row.rank}
                          </span>
                          <span className="truncate font-headline text-sm font-medium text-on-surface transition-colors group-hover:text-primary">
                            {row.songName}
                          </span>
                        </div>
                        <span className="shrink-0 rounded-full bg-surface-container px-2.5 py-0.5 font-mono text-xs font-medium text-on-surface-variant">
                          {row.currentGap !== null ? row.currentGap : "-"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="editorial-chip mt-5 rounded-[1.5rem] border-dashed p-6 text-center">
                <p className="font-headline text-lg text-on-surface">
                  Live preview unavailable
                </p>
                <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                  {predictionState.status === "missing_env"
                    ? "Set SUPABASE_URL and SUPABASE_ANON_KEY to load the teaser."
                    : "The teaser requires a current prediction snapshot."}
                </p>
                <Link
                  href={bandPath(band, "predictions")}
                  className="mt-4 inline-block rounded-full border border-outline-variant/40 bg-surface-container-low px-4 py-2 font-headline text-xs font-bold uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary hover:text-primary focus-visible:ring-2 focus-visible:ring-primary focus-visible:outline-none"
                >
                  Open full board
                </Link>
              </div>
            )}
    </>
  );
}
