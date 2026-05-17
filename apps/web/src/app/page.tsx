import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { SectionCard } from "@/components/section-card";
import {
  getBands,
  getLatestPredictions,
  getNextShowDetails,
} from "@/lib/data";
import { buildLocationLabel, formatDateLabel } from "@/lib/format";

export const dynamic = "force-dynamic";

const HOME_TEASER_BANDS = [
  { slug: "phish", label: "Phish", fallbackName: "Phish" },
  { slug: "wsp", label: "WSP", fallbackName: "Widespread Panic" },
  { slug: "billy", label: "Billy", fallbackName: "Billy Strings" },
  { slug: "goose", label: "Goose", fallbackName: "Goose" },
] as const;

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Collect setlist data",
    body: "Historical setlists are collected and normalized into a shared format across supported bands.",
  },
  {
    step: "02",
    title: "Score the next show",
    body: "For each band, a model ranks songs for the next target show using setlist history, tour information, and current context.",
  },
  {
    step: "03",
    title: "Track what landed",
    body: "Completed shows feed the performance ledger and replay views so the public board stays accountable.",
  },
] as const;

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

export default async function HomePage({ searchParams }: Props) {
  const params = await searchParams;

  if (params.band) {
    redirect(`/predictions?band=${params.band}`);
  }

  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const requestedTeaser = params.teaser?.trim().toLowerCase();
  const teaserConfig =
    HOME_TEASER_BANDS.find((band) => band.slug === requestedTeaser) ??
    HOME_TEASER_BANDS[0];
  const teaserBandSlug = teaserConfig.slug;
  const teaserBandEntry = bands.find((band) => band.slug === teaserBandSlug) ?? {
    slug: teaserBandSlug,
    displayName: teaserConfig.fallbackName,
  };

  const [teaserPredictionState, teaserNextShowState] = await Promise.all([
    getLatestPredictions(teaserBandSlug),
    getNextShowDetails(teaserBandSlug),
  ]);
  const teaserNextShow =
    teaserNextShowState.status === "ready" ? teaserNextShowState.show : null;
  const teaserSongs =
    teaserPredictionState.status === "ready"
      ? teaserPredictionState.snapshot.predictions.slice(0, 3)
      : [];
  const teaserLocationLabel = buildLocationLabel([
    teaserNextShow?.city ?? null,
    teaserNextShow?.state ?? teaserNextShow?.country ?? null,
  ]);

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-0">
      <section className="editorial-hero px-6 py-8 md:px-10 md:py-16">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,191,105,0.22),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(136,229,216,0.12),transparent_26%),linear-gradient(135deg,rgba(255,255,255,0.04),transparent_55%)]" />
        <div className="relative grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:items-center">
          <div className="flex h-full flex-col justify-center">
            <h1 className="max-w-3xl font-headline text-4xl font-bold uppercase leading-tight tracking-[-0.05em] text-on-surface md:text-6xl lg:text-7xl">
              What are they playing next?
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-relaxed text-on-surface-variant">
              See how each band&apos;s model ranks the next show, then track
              avg. hits, coverage, and replay results after the setlist lands.
            </p>
            <div className="mt-8 hidden gap-4 md:grid md:max-w-3xl md:grid-cols-2">
              <Link
                href="/predictions"
                className="inline-flex w-full items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3.5 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary"
              >
                View Predictions
              </Link>
              <Link
                href="/performance"
                className="inline-flex w-full items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3.5 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary"
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
              {HOME_TEASER_BANDS.map((band) => {
                const isActive = band.slug === teaserBandSlug;
                return (
                  <Link
                    key={band.slug}
                    href={`/?teaser=${band.slug}`}
                    scroll={false}
                    className={`flex items-center justify-center rounded-full border px-2.5 py-2 text-center font-headline text-[10px] font-bold uppercase tracking-[0.12rem] transition ${
                      isActive
                        ? "border-primary/30 bg-primary/12 text-primary"
                        : "border-transparent bg-surface-container-low text-on-surface-variant hover:bg-outline-variant/20 hover:text-on-surface"
                    }`}
                  >
                    {band.label}
                  </Link>
                );
              })}
            </div>

            {teaserPredictionState.status === "ready" ? (
              <>
                <div className="editorial-chip mt-5 rounded-[1.5rem] p-4">
                  <p className="font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant/70">
                    Next Show
                  </p>
                  <p className="mt-1.5 font-headline text-xl font-bold text-primary md:text-2xl">
                    {formatDateLabel(
                      teaserNextShow?.showDate ??
                        teaserPredictionState.snapshot.targetShowDate,
                    )}
                  </p>
                  <p className="mt-1 font-headline text-base text-on-surface">
                    {teaserNextShow?.venueName ??
                      `${teaserBandEntry.displayName} next show`}
                  </p>
                  <p className="mt-0.5 text-xs text-on-surface-variant">
                    {teaserLocationLabel ?? "Location unavailable"}
                  </p>
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
                    {teaserSongs.map((row) => (
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
                  {teaserPredictionState.status === "missing_env"
                    ? "Set SUPABASE_URL and SUPABASE_ANON_KEY to load the teaser."
                    : "The teaser requires a current prediction snapshot."}
                </p>
                <Link
                  href="/predictions"
                  className="mt-4 inline-block rounded-full border border-outline-variant/40 bg-surface-container-low px-4 py-2 font-headline text-xs font-bold uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary hover:text-primary"
                >
                  Open full board
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>

      {bandsResult.status !== "ready" ? (
        <SectionCard title="Band registry unavailable" eyebrow="Data status">
          <p className="text-sm leading-6 text-on-surface-variant">
            {bandsResult.status === "missing_env"
              ? "Set SUPABASE_URL and SUPABASE_ANON_KEY to load the supported bands."
              : bandsResult.status === "error"
                ? bandsResult.message
                : "No active bands were returned from the bands table."}
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

      <SectionCard title="How Predictions Work">
        <div className="grid gap-6 md:grid-cols-3">
          {HOW_IT_WORKS.map((item) => (
            <div
              key={item.step}
              className="editorial-chip flex flex-col rounded-[1.5rem] p-6 transition-colors hover:border-primary/30"
            >
              <div className="mb-4 inline-flex size-9 items-center justify-center rounded-full bg-surface-container font-mono text-sm font-bold text-primary/80">
                {item.step}
              </div>
              <p className="font-headline text-lg font-bold text-on-surface">
                {item.title}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-on-surface-variant">
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </SectionCard>

      {bands.length > 0 && (
        <SectionCard title="Artists We Track">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {bands.map((band) => (
              <Link
                key={band.slug}
                href={`/predictions?band=${band.slug}`}
                className="editorial-chip flex items-center justify-center rounded-[1.5rem] p-5 text-center transition-all hover:border-primary hover:bg-surface-container-high hover:shadow-md"
              >
                <span className="font-headline text-lg font-bold text-on-surface transition-colors hover:text-primary">
                  {band.displayName}
                </span>
              </Link>
            ))}
          </div>
        </SectionCard>
      )}

    </div>
  );
}
