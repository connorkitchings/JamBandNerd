import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { DataState } from "@/components/data-state";
import { SectionCard } from "@/components/section-card";
import { getBands } from "@/lib/data";

export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<{
    band?: string;
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

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-0">
      <section className="editorial-hero px-6 py-8 md:px-10 md:py-14">
        <div className="relative max-w-4xl">
          <span className="editorial-kicker">JamBandNerd</span>
          <h1 className="mt-4 max-w-3xl font-headline text-4xl font-bold uppercase leading-tight tracking-[-0.05em] text-on-surface md:text-6xl lg:text-7xl">
            What are they playing next?
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-on-surface-variant">
            Setlist predictions, recent model performance, and replayable
            prediction history for supported bands.
          </p>
          <div className="mt-8 grid gap-4 sm:max-w-xl sm:grid-cols-2">
            <Link
              href="/predictions"
              className="inline-flex min-h-12 items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary"
            >
              View Predictions
            </Link>
            <Link
              href="/replay"
              className="inline-flex min-h-12 items-center justify-center rounded-full border border-outline-variant/35 bg-surface/70 px-6 py-3 text-center font-headline text-sm font-medium uppercase tracking-[0.14rem] text-on-surface transition hover:border-primary/35 hover:bg-surface-container-low hover:text-primary"
            >
              Replay History
            </Link>
          </div>
        </div>
      </section>

      {bandsResult.status === "ready" ? (
        <SectionCard title="Supported Bands">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {bands.map((band) => (
              <Link
                key={band.slug}
                href={`/predictions?band=${band.slug}`}
                className="editorial-chip flex min-h-16 items-center justify-between rounded-xl px-4 py-3 transition hover:border-primary hover:bg-surface-container-high"
              >
                <span className="font-headline text-base font-semibold text-on-surface">
                  {band.displayName}
                </span>
                <span className="font-label text-[10px] uppercase tracking-[0.16em] text-on-surface-variant">
                  Predict
                </span>
              </Link>
            ))}
          </div>
        </SectionCard>
      ) : (
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
