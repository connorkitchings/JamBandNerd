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
    <div className="mx-auto max-w-6xl space-y-12 pb-10">
      <section className="relative overflow-hidden rounded-[32px] border border-outline-variant/30 bg-surface-container px-6 py-8 shadow-[0_24px_80px_rgba(0,0,0,0.08)] md:px-10 md:py-16">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,205,110,0.22),transparent_32%),radial-gradient(circle_at_bottom_right,rgba(255,140,80,0.16),transparent_30%),linear-gradient(135deg,rgba(255,255,255,0.04),transparent_55%)]" />
        <div className="relative grid gap-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] lg:items-center">
          <div className="flex h-full flex-col justify-center">
            <div className="flex flex-col gap-8">
              <div>
                <p className="font-label text-[11px] font-bold uppercase tracking-[0.24em] text-primary">
                  JamBandNerd
                </p>
                <h1 className="mt-4 max-w-3xl font-headline text-4xl font-bold uppercase tracking-[-0.04em] text-on-surface md:text-6xl lg:text-7xl leading-tight">
                  What are they playing next?
                </h1>
                <p className="mt-5 max-w-2xl text-lg leading-relaxed text-on-surface-variant">
                  Data-driven setlist predictions for your favorite jam bands. Track historical performance, explore venue trends, and see what the models think is coming.
                </p>
                <div className="mt-8 flex flex-wrap gap-4">
                  <Link
                    href="/predictions"
                    className="inline-flex items-center justify-center rounded-full border border-outline-variant/40 bg-surface/70 px-6 py-3.5 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary hover:text-primary hover:bg-surface-container-low"
                  >
                    View Predictions
                  </Link>
                  <Link
                    href="/performance"
                    className="inline-flex items-center justify-center rounded-full border border-outline-variant/40 bg-surface/70 px-6 py-3.5 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary hover:text-primary hover:bg-surface-container-low"
                  >
                    See Performance
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <div className="rounded-[28px] border border-outline-variant/30 bg-surface/85 p-6 shadow-xl backdrop-blur-md">
            <p className="mb-4 font-label text-[10px] font-bold uppercase tracking-[0.24em] text-primary/80">
              Live Teasers
            </p>
            <div className="grid grid-cols-4 gap-2">
              {HOME_TEASER_BANDS.map((band) => {
                const isActive = band.slug === teaserBandSlug;
                return (
                  <Link
                    key={band.slug}
                    href={`/?teaser=${band.slug}`}
                    className={`rounded-full border px-2.5 py-1 flex items-center justify-center text-center font-headline text-[10px] font-bold uppercase tracking-[0.12rem] transition ${
                      isActive
                        ? "border-primary bg-primary/15 text-primary"
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
                <div className="mt-5 rounded-2xl border border-outline-variant/20 bg-surface/50 p-4">
                  <p className="font-label text-[10px] font-medium uppercase tracking-[0.18rem] text-on-surface-variant/70">
                    Next Show
                  </p>
                  <p className="mt-1.5 font-headline text-xl font-bold text-primary md:text-2xl">
                    {formatDateLabel(
                      teaserNextShow?.showDate ??
                        teaserPredictionState.snapshot.referenceDate,
                    )}
                  </p>
                  <p className="mt-1 font-headline text-base text-on-surface">
                    {teaserNextShow?.venueName ?? "Venue TBA"}
                  </p>
                  <p className="mt-0.5 text-xs text-on-surface-variant">
                    {teaserLocationLabel ?? "Location unavailable"}
                  </p>
                </div>

                <div className="mt-4 rounded-2xl border border-outline-variant/20 bg-surface/50 p-4">
                  <div className="flex items-center justify-between mb-3 border-b border-outline-variant/15 pb-2">
                    <p className="font-label text-[10px] font-medium uppercase tracking-[0.16rem] text-on-surface-variant/70">
                      Top Picks (Notebook)
                    </p>
                    <p className="font-label text-[10px] font-medium uppercase tracking-[0.16rem] text-on-surface-variant/70">
                      Current Gap
                    </p>
                  </div>
                  <div className="space-y-2.5">
                    {teaserSongs.map((row) => (
                      <div
                        key={`${row.rank}-${row.songName}`}
                        className="flex items-center justify-between group"
                      >
                        <div className="flex items-center gap-3">
                          <span className="flex h-5 w-5 items-center justify-center rounded bg-surface-container font-headline text-xs font-bold text-on-surface-variant">
                            {row.rank}
                          </span>
                          <span className="font-headline text-sm font-medium text-on-surface group-hover:text-primary transition-colors">
                            {row.songName}
                          </span>
                        </div>
                        <div className="flex items-center">
                          <span className="rounded bg-surface-container px-2 py-0.5 font-mono text-xs font-medium text-on-surface-variant">
                            {row.currentGap !== null ? row.currentGap : "-"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="mt-5 rounded-2xl border border-dashed border-outline-variant/30 bg-surface/50 p-6 text-center">
                <p className="font-headline text-lg text-on-surface">
                  Live preview unavailable
                </p>
                <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                  The teaser requires server-side data access.
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

      {/* Stats Ribbon */}
      <section className="grid grid-cols-2 gap-4 md:grid-cols-3">
        <div className="flex flex-col justify-center rounded-2xl border border-outline-variant/20 bg-surface-container px-6 py-5 text-center">
          <p className="font-headline text-3xl font-bold text-on-surface">
            {bands.length || "—"}
          </p>
          <p className="mt-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant">
            Bands Tracked
          </p>
        </div>
        <div className="flex flex-col justify-center rounded-2xl border border-outline-variant/20 bg-surface-container px-6 py-5 text-center">
          <p className="font-headline text-3xl font-bold text-on-surface">
            {ACTIVE_MODELS.length}
          </p>
          <p className="mt-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant">
            Prediction Models
          </p>
        </div>
        <div className="col-span-2 flex flex-col justify-center rounded-2xl border border-outline-variant/20 bg-surface-container px-6 py-5 text-center md:col-span-1">
          <p className="font-headline text-3xl font-bold text-on-surface">Daily</p>
          <p className="mt-1 font-label text-[10px] font-bold uppercase tracking-[0.18rem] text-on-surface-variant">
            Refresh Cadence
          </p>
        </div>
      </section>

      <SectionCard title="How It Works">
        <div className="grid gap-6 md:grid-cols-3">
          {HOW_IT_WORKS.map((item) => (
            <div
              key={item.step}
              className="flex flex-col rounded-2xl border border-outline-variant/15 bg-surface/50 p-6 transition-colors hover:border-primary/30 hover:bg-surface-container-low"
            >
              <div className="mb-4 inline-flex h-8 w-8 items-center justify-center rounded-full bg-surface-container font-mono text-sm font-bold text-primary/80">
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

      <SectionCard title="Supported Bands">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {bands.map((band) => (
            <Link
              key={band.slug}
              href={`/predictions?band=${band.slug}`}
              className="flex items-center justify-center rounded-2xl border border-outline-variant/20 bg-surface-container p-5 text-center transition-all hover:border-primary hover:bg-surface-container-high hover:shadow-md"
            >
              <span className="font-headline text-lg font-bold text-on-surface transition-colors hover:text-primary">
                {band.displayName}
              </span>
            </Link>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
