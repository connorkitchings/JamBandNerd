import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { SectionCard } from "@/components/section-card";
import { ACTIVE_MODELS } from "@/lib/config";
import {
  bandEntryBySlug,
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

const ENTRY_CARDS = [
  {
    title: "Predictions",
    href: "/predictions",
    body: "Open the full next-show board with live rankings, search, and model switching.",
  },
  {
    title: "Performance",
    href: "/performance",
    body: "Review historical recall and see how each model has been scoring over time.",
  },
  {
    title: "Deep-Dive",
    href: "/venues",
    body: "Open explorer, venue patterns, and model comparison tools for deeper analysis.",
  },
] as const;

const HOW_IT_WORKS = [
  {
    step: "01",
    title: "Track setlists",
    body: "JamBandNerd collects and normalizes historical show data across supported bands.",
  },
  {
    step: "02",
    title: "Rank songs",
    body: "Multiple models rank songs from different angles to estimate what could appear next.",
  },
  {
    step: "03",
    title: "Review outcomes",
    body: "Use the site to compare predictions, explore past shows, and track model performance.",
  },
] as const;

type Props = {
  searchParams: Promise<{
    band?: string;
    model?: string;
    teaser?: string;
  }>;
};

export const metadata: Metadata = {
  title: "JamBandNerd | Forward-Looking Setlist Predictions",
  description:
    "Setlist predictions for the next show, with supporting performance and historical analysis tools for jam bands.",
};

export default async function HomePage({ searchParams }: Props) {
  const params = await searchParams;
  const query = new URLSearchParams();

  if (params.band) {
    query.set("band", params.band);
  }

  if (params.model) {
    query.set("model", params.model);
  }

  if (query.size > 0) {
    redirect(`/predictions${query.toString() ? `?${query}` : ""}`);
  }

  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  const requestedTeaser = params.teaser?.trim().toLowerCase();
  const teaserConfig =
    HOME_TEASER_BANDS.find((band) => band.slug === requestedTeaser) ??
    HOME_TEASER_BANDS[0];
  const teaserBandSlug = teaserConfig.slug;
  const teaserBandEntry = bandEntryBySlug(bands, teaserBandSlug) ?? {
    slug: teaserBandSlug,
    displayName: teaserConfig.fallbackName,
    showsTable: "",
    idColumn: "",
  };

  const teaserPredictionState = await getLatestPredictions(teaserBandSlug, "notebook");
  const teaserNextShowState = await getNextShowDetails(teaserBandSlug);
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
    <div className="mx-auto max-w-6xl space-y-8 pb-10">
      <section className="relative overflow-hidden rounded-[32px] border border-outline-variant/30 bg-surface-container px-6 py-8 shadow-[0_24px_80px_rgba(0,0,0,0.08)] md:px-10 md:py-12">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,205,110,0.22),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(255,140,80,0.16),transparent_30%),linear-gradient(135deg,rgba(255,255,255,0.04),transparent_55%)]" />
        <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:items-stretch">
          <div className="flex h-full flex-col justify-center">
            <div className="flex flex-col gap-10">
              <div>
              <p className="font-label text-[10px] uppercase tracking-[0.24em] text-primary">
                Setlist predictions for the next show
              </p>
              <h1 className="mt-4 max-w-3xl font-headline text-5xl font-bold uppercase tracking-[-0.08em] text-on-surface md:text-7xl">
                JamBandNerd
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-on-surface-variant">
                Get next-show setlist predictions for jam bands, with performance,
                explorer, and venue tools to help explain the board.
              </p>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <Link
                href="/predictions"
                className="rounded-full border border-outline-variant/30 bg-surface/70 px-5 py-3 text-center font-headline text-sm uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary hover:text-primary"
              >
                View Predictions
              </Link>
                <Link
                  href="/performance"
                  className="rounded-full border border-outline-variant/30 bg-surface/70 px-5 py-3 text-center font-headline text-sm uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary hover:text-primary"
                >
                  See Performance
                </Link>
              </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-outline-variant/20 bg-surface/75 px-4 py-4 text-center">
                  <p className="font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                    Bands tracked
                  </p>
                  <p className="mt-2 font-headline text-2xl text-on-surface">
                    {bands.length || "—"}
                  </p>
                </div>
                <div className="rounded-2xl border border-outline-variant/20 bg-surface/75 px-4 py-4 text-center">
                  <p className="font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                    Prediction models
                  </p>
                  <p className="mt-2 font-headline text-2xl text-on-surface">
                    {ACTIVE_MODELS.length}
                  </p>
                </div>
                <div className="rounded-2xl border border-outline-variant/20 bg-surface/75 px-4 py-4 text-center">
                  <p className="font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                    Refresh cadence
                  </p>
                  <p className="mt-2 font-headline text-2xl text-on-surface">Daily</p>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-[28px] border border-outline-variant/25 bg-surface/82 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-sm">
            <p className="font-label text-[10px] uppercase tracking-[0.24em] text-primary">
              Teasers
            </p>
            <div className="mt-4 grid grid-cols-4 gap-2">
              {HOME_TEASER_BANDS.map((band) => {
                const isActive = band.slug === teaserBandSlug;
                return (
                  <Link
                    key={band.slug}
                    href={`/?teaser=${band.slug}`}
                    className={`rounded-full border px-2 py-1.5 text-center font-headline text-xs uppercase tracking-[0.12rem] transition ${
                      isActive
                        ? "border-primary bg-primary/12 text-primary"
                        : "border-outline-variant/30 bg-surface-container-low text-on-surface-variant hover:border-primary hover:text-on-surface"
                    }`}
                  >
                    {band.label}
                  </Link>
                );
              })}
            </div>
            <h2 className="mt-4 text-center font-headline text-2xl font-semibold uppercase tracking-[-0.05em] text-on-surface">
              {teaserBandEntry.displayName}
            </h2>

            {teaserPredictionState.status === "ready" ? (
              <>
                <div className="mt-5 rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-4">
                  <p className="text-center font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                    Next show
                  </p>
                  <p className="mt-3 text-center font-headline text-2xl text-on-surface md:text-3xl">
                    {formatDateLabel(
                      teaserNextShow?.showDate ??
                        teaserPredictionState.snapshot.referenceDate,
                    )}
                  </p>
                  <p className="mt-2 text-center font-headline text-lg text-on-surface">
                    {teaserNextShow?.venueName ?? `${teaserBandEntry.displayName} next show`}
                  </p>
                  <p className="mt-1 text-center text-sm text-on-surface-variant">
                    {teaserLocationLabel ?? "Location unavailable"}
                  </p>
                </div>

                <div className="mt-4 rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-4">
                  <p className="text-center font-label text-[10px] uppercase tracking-[0.18rem] text-on-surface-variant">
                    Top predictions
                  </p>
                  <div className="mt-3 flex items-center justify-between gap-4 border-b border-outline-variant/15 pb-2">
                    <div className="flex items-center gap-3">
                      <span className="w-4" aria-hidden="true" />
                      <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                        Song
                      </p>
                    </div>
                    <p className="font-label text-[10px] uppercase tracking-[0.16rem] text-on-surface-variant">
                      Current Gap
                    </p>
                  </div>
                  <div className="mt-3 space-y-3">
                    {teaserSongs.map((row) => (
                      <div
                        key={`${row.rank}-${row.songName}`}
                        className="flex items-center justify-between gap-4"
                      >
                        <div className="flex items-center gap-3">
                          <span className="w-4 text-center font-headline text-sm tabular-nums text-on-surface/55">
                            {row.rank}
                          </span>
                          <span className="font-headline text-sm text-on-surface">
                            {row.songName}
                          </span>
                        </div>
                        <span className="text-xs text-on-surface-variant">
                          {row.currentGap !== null
                            ? `${row.currentGap} ${row.currentGap === 1 ? "show" : "shows"}`
                            : "gap unknown"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-outline-variant/20 bg-surface-container-low px-4 py-5">
                <p className="font-headline text-lg text-on-surface">
                  Live preview unavailable
                </p>
                <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                  The homepage still works without live prediction data, but the live teaser
                  will appear only when server-side prediction reads are available.
                </p>
                <Link
                  href="/predictions"
                  className="mt-4 inline-flex rounded-full border border-outline-variant/30 px-4 py-2 font-headline text-xs uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary hover:text-primary"
                >
                  Open predictions
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>

      <SectionCard title="Start Here" centered>
        <div className="grid gap-4 md:grid-cols-3">
          {ENTRY_CARDS.map((item) => (
            <Link
              key={item.title}
              href={item.href}
              className="rounded-2xl border border-outline-variant/20 bg-surface-container-low p-5 transition hover:border-primary hover:bg-surface-container"
            >
              <p className="font-headline text-xl font-medium text-on-surface">{item.title}</p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">{item.body}</p>
            </Link>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="How Predictions Work" centered>
        <div className="grid gap-4 md:grid-cols-3">
          {HOW_IT_WORKS.map((item) => (
            <div
              key={item.step}
              className="rounded-2xl border border-outline-variant/20 bg-surface-container-low p-5"
            >
              <p className="font-headline text-3xl text-primary/30">{item.step}</p>
              <p className="mt-3 font-headline text-lg font-medium text-on-surface">
                {item.title}
              </p>
              <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                {item.body}
              </p>
            </div>
          ))}
        </div>
      </SectionCard>

      <SectionCard title="Supported Bands" centered>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {bands.map((band) => (
            <Link
              key={band.slug}
              href={`/predictions?band=${band.slug}`}
              className="rounded-2xl border border-outline-variant/20 bg-surface-container-low p-4 text-center transition hover:border-primary hover:bg-surface-container"
            >
              <p className="font-headline text-lg font-medium text-on-surface">
                {band.displayName}
              </p>
            </Link>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
