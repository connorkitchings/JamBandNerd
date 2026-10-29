import type { Metadata } from "next";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense, cache } from "react";

import { BandPillGrid } from "@/components/band-pill-grid";
import { MetricCard } from "@/components/metric-card";
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

const HOW_IT_WORKS = [
  {
    step: "1",
    title: "Gather the setlists",
    body: "We pull in setlist history for every band we cover: what was played, when, and where.",
  },
  {
    step: "2",
    title: "Guess the next show",
    body: "A model built from years of setlist history looks at rotation, gaps, and venue habits to rank the likeliest songs.",
  },
  {
    step: "3",
    title: "See what happened",
    body: "After the show, we check the board against the real setlist so you can see what landed and what didn't.",
  },
] as const;

const BUTTON_BASE =
  "inline-flex min-h-11 items-center justify-center rounded-full px-6 py-2 text-sm font-bold transition";
const BUTTON_PRIMARY = `${BUTTON_BASE} bg-accent text-on-accent hover:brightness-95`;
const BUTTON_SECONDARY = `${BUTTON_BASE} border border-line text-on-surface hover:bg-surface-2`;

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
    <div className="mx-auto max-w-6xl space-y-10 pb-0">
      {bands.length > 0 && (
        <nav aria-label="Band" className="-mb-4 pt-4 lg:pt-8">
          <BandPillGrid
            layout="row"
            links={bands.map((item) => ({
              href: bandPath(item.slug),
              label: item.displayName,
              active: item.slug === band,
            }))}
          />
        </nav>
      )}

      <section className="grid gap-8 pt-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,1fr)] lg:items-stretch lg:pt-8">
        <div className="flex flex-col justify-center">
          <p className="text-xs font-bold uppercase tracking-[0.08em] text-accent-text">
            {bandEntry.displayName} · Next show
          </p>
          <h1 className="mt-2 text-3xl font-bold text-on-surface md:text-4xl">
            What are they playing next?
          </h1>
          <p className="mt-3 max-w-xl text-base text-on-surface-variant">
            We rank the songs each band might play at the next show. It&apos;s an educated guess,
            sometimes right and sometimes not, but always worth checking.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link href={bandPath(band, "predictions")} className={BUTTON_PRIMARY}>
              See the predictions
            </Link>
            <Link href={bandPath(band, "performance")} className={BUTTON_SECONDARY}>
              See performance
            </Link>
          </div>
        </div>

        <Suspense
          fallback={<div aria-hidden="true" className="h-48 animate-pulse rounded-xl bg-surface-2" />}
        >
          <NextShowCard band={band} bandName={bandEntry.displayName} />
        </Suspense>
      </section>

      {bands.length === 0 ? (
        <SectionCard title="Band registry unavailable" eyebrow="Data status">
          <p className="text-sm text-on-surface-variant">
            We couldn&apos;t load the supported bands right now. Please try again in a few minutes.
          </p>
        </SectionCard>
      ) : null}

      <section aria-labelledby="first-look">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="first-look" className="text-2xl font-bold text-on-surface">
            First look
          </h2>
          <Link
            href={bandPath(band, "predictions")}
            className="inline-flex min-h-11 items-center text-sm font-semibold text-accent-text underline"
          >
            Full board
          </Link>
        </div>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <Suspense
            fallback={<div aria-hidden="true" className="h-56 animate-pulse rounded-xl bg-surface-2" />}
          >
            <TopPicksCard band={band} />
          </Suspense>
          <div className="flex flex-col gap-4">
            <MetricCard label="Bands tracked" value={String(bands.length || "-")} />
            <MetricCard label="Refresh cadence" value="Daily" />
          </div>
        </div>
      </section>

      <section aria-labelledby="how-it-works">
        <h2 id="how-it-works" className="mb-4 text-2xl font-bold text-on-surface">
          How it works
        </h2>
        <div className="grid gap-4 md:grid-cols-3">
          {HOW_IT_WORKS.map((item) => (
            <div key={item.step} className="rounded-xl border border-line bg-surface p-5">
              <span className="inline-flex size-8 items-center justify-center rounded-full border border-line bg-surface-2 text-sm font-bold text-on-surface">
                {item.step}
              </span>
              <h3 className="mt-3 text-lg font-bold text-on-surface">{item.title}</h3>
              <p className="mt-2 text-sm text-on-surface-variant">{item.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/**
 * Request-time teaser data shared by the next-show card and the top-picks card;
 * cached per render so both cards reuse one set of queries.
 */
const loadTeaser = cache(async (band: string) => {
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

  return { predictionState, targetDate, missingShows, nextShow, songs };
});

function TeaserUnavailable({
  band,
  status,
}: {
  band: string;
  status: "missing_env" | "error" | "empty" | "ready";
}) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface p-5">
      <p className="text-lg font-bold text-on-surface">Live preview unavailable</p>
      <p className="mt-2 text-sm text-on-surface-variant">
        {status === "missing_env"
          ? "Set SUPABASE_URL and SUPABASE_ANON_KEY to load the teaser."
          : "The teaser requires a current prediction snapshot."}
      </p>
      <Link
        href={bandPath(band, "predictions")}
        className="mt-4 inline-flex min-h-11 items-center justify-center rounded-full border border-line px-5 text-sm font-bold text-on-surface transition hover:bg-surface-2"
      >
        Open full board
      </Link>
    </div>
  );
}

/** Date, venue and location of the show the latest prediction snapshot targets. */
async function NextShowCard({ band, bandName }: { band: string; bandName: string }) {
  const { predictionState, targetDate, missingShows, nextShow } = await loadTeaser(band);

  if (predictionState.status !== "ready" || targetDate === null) {
    return <TeaserUnavailable band={band} status={predictionState.status} />;
  }

  const locationLabel = buildLocationLabel([
    nextShow?.city ?? null,
    nextShow?.state ?? nextShow?.country ?? null,
  ]);

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-5">
      <p className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
        Next show
      </p>
      <p className="text-2xl font-bold text-on-surface">{formatDateLabel(targetDate)}</p>
      <div>
        <p className="text-base text-on-surface">{nextShow?.venueName || `${bandName} next show`}</p>
        <p className="text-sm text-on-surface-variant">{locationLabel || "Location unavailable"}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <span className="inline-block rounded-full border border-teal bg-teal-bg px-3 py-0.5 text-xs font-bold text-teal">
          Prediction ready
        </span>
      </div>
      {missingShows.length > 0 && (
        <p
          role="status"
          className="rounded-md border border-accent-text bg-amber-bg px-3 py-2 text-xs text-accent-text"
        >
          Awaiting upstream setlist for{" "}
          {missingShows.map((show) => formatCompactDateLabel(show.showDate)).join(", ")}
        </p>
      )}
    </div>
  );
}

/** Top three predicted songs with their current gap. */
async function TopPicksCard({ band }: { band: string }) {
  const { predictionState, songs } = await loadTeaser(band);

  if (predictionState.status !== "ready") {
    return (
      <div className="rounded-xl border border-dashed border-line bg-surface p-5">
        <p className="text-sm text-on-surface-variant">
          Top picks appear here once a current prediction snapshot is available.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-line bg-surface p-5">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
          Top 3 picks
        </p>
        <p className="text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
          Current gap
        </p>
      </div>
      <ol>
        {songs.map((row) => (
          <li
            key={`${row.rank}-${row.songName}`}
            className="flex items-center gap-3 border-t border-line py-3 first:border-t-0"
          >
            <span className="w-7 text-sm font-bold tabular-nums text-on-surface-variant">
              {row.rank}
            </span>
            <span className="min-w-0 flex-1 truncate font-semibold text-on-surface">
              {row.songName}
            </span>
            <span className="shrink-0 font-bold tabular-nums text-on-surface">
              {row.currentGap !== null ? row.currentGap : "-"}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
