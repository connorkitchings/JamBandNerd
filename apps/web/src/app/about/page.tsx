import type { Metadata } from "next";
import Link from "next/link";

import { SectionCard } from "@/components/section-card";
import { MODEL_CONFIG } from "@/lib/config";
import { getBands } from "@/lib/data";

export const metadata: Metadata = {
  title: "About | JamBandNerd",
  description: "Learn how JamBandNerd collects setlists, transforms data, and generates predictions.",
};



const FAQ_ITEMS = [
  {
    question: "How often are predictions updated?",
    answer:
      "The pipeline runs daily at 3 PM ET via GitHub Actions. Each run collects the latest setlist data, re-generates predictions for every supported band and model, and publishes them to Supabase.",
  },
  {
    question: "What do the likelihood tiers mean?",
    answer:
      "Tiers (Expected, Hot, Likely, Possible) reflect relative ranking position rather than a precise probability. Expected songs have the strongest rotation signal, while Possible songs have lower recent activity but could still appear.",
  },
  {
    question: "Where does the setlist data come from?",
    answer:
      "Each band has a dedicated collector. Sources include Phish.net, El Goose, setlist.fm, Every Day Companion, and other community-maintained archives. The pipeline normalizes all data into a shared show-centric format.",
  },
  {
    question: "Can I use this data for my own projects?",
    answer:
      "The project is open-source under the MIT license. Check out the GitHub repository for the full codebase, documentation, and contribution guidelines.",
  },
  {
    question: "How is accuracy measured?",
    answer:
      "After each show, the pipeline compares predictions against the actual setlist. Recall is measured at Top-10, Top-25, and Top-50 windows — meaning how many of the top-K predicted songs actually appeared.",
  },
];

const PIPELINE_STEPS = [
  {
    step: "01",
    title: "Collect",
    description: "Band-specific collectors pull the latest setlist data from community archives.",
  },
  {
    step: "02",
    title: "Transform",
    description:
      "Raw data is normalized into a shared show-centric format with gap calculations and rotation signals.",
  },
  {
    step: "03",
    title: "Predict",
    description:
      "Multiple models rank every song in the catalog by likelihood of appearing at the next show.",
  },
  {
    step: "04",
    title: "Publish",
    description:
      "Predictions, accuracy scores, and setlists are written to Supabase and served to this website.",
  },
];

export default async function AboutPage() {
  const bandsResult = await getBands();
  const bands = bandsResult.status === "ready" ? bandsResult.bands : [];
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-container p-8 md:p-12">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-gradient-to-l from-primary-container/15 to-transparent lg:block" />
        <div className="relative">
          <p className="font-label text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
            About the platform
          </p>
          <h1 className="mt-3 font-headline text-4xl font-semibold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
            About JamBandNerd
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-on-surface-variant">
            JamBandNerd is a data platform that collects jam band setlists, transforms them through
            feature-engineered pipelines, and generates next-show predictions. The system runs daily,
            tracking rotation patterns, song gaps, and historical cadences to rank every song in a
            band&rsquo;s catalog by likelihood of appearing at the next show.
          </p>
          <p className="mt-3 max-w-3xl text-sm leading-7 text-on-surface-variant">
            This website is the primary public surface — browse real-time predictions, explore
            historical snapshots, compare models side-by-side, and track accuracy over time.
          </p>
        </div>
      </section>

      {/* Model Explainers */}
      <SectionCard title="Prediction Models" eyebrow="How It Works">
        <p className="mb-6 text-sm leading-6 text-on-surface-variant">
          Two models generate independent predictions for every band. Each approaches the
          problem from a different angle, letting you compare outputs and spot consensus.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          {(Object.entries(MODEL_CONFIG) as [string, (typeof MODEL_CONFIG)[keyof typeof MODEL_CONFIG]][]).map(
            ([slug, model]) => (
              <div
                key={slug}
                className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-6"
              >
                <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
                  {model.displayName}
                </p>
                <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                  {model.explanation}
                </p>
              </div>
            ),
          )}
        </div>
      </SectionCard>

      {/* Supported Bands */}
      <SectionCard
        title="Supported Bands"
        eyebrow={`${bands.length} bands tracked`}
      >
        <p className="mb-6 text-sm leading-6 text-on-surface-variant">
          The pipeline dynamically discovers and runs for each supported band. Tap one
          to jump to its latest predictions.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {bands.map((band) => (
            <Link
              key={band.slug}
              href={`/?band=${band.slug}`}
              className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-4 transition hover:border-primary hover:bg-surface-container"
            >
              <p className="font-headline text-lg font-medium text-on-surface">
                {band.displayName}
              </p>
              <p className="mt-1 text-xs text-on-surface-variant">View predictions →</p>
            </Link>
          ))}
        </div>
      </SectionCard>

      {/* Pipeline Overview */}
      <SectionCard title="The Pipeline" eyebrow="Daily Automation">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE_STEPS.map((item) => (
            <div
              key={item.step}
              className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5"
            >
              <p className="font-headline text-3xl font-bold text-primary/30">{item.step}</p>
              <p className="mt-2 font-headline text-base font-semibold text-on-surface">
                {item.title}
              </p>
              <p className="mt-2 text-xs leading-5 text-on-surface-variant">{item.description}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* FAQ */}
      <SectionCard title="FAQ" eyebrow="Common Questions">
        <div className="space-y-4">
          {FAQ_ITEMS.map((item) => (
            <details
              key={item.question}
              className="group rounded-xl border border-outline-variant/20 bg-surface-container-low"
            >
              <summary className="cursor-pointer select-none px-5 py-4 font-headline text-sm font-medium text-on-surface transition group-open:text-primary">
                {item.question}
              </summary>
              <p className="px-5 pb-4 text-sm leading-6 text-on-surface-variant">{item.answer}</p>
            </details>
          ))}
        </div>
      </SectionCard>

      {/* Links */}
      <SectionCard title="Links" eyebrow="Resources">
        <div className="grid gap-3 sm:grid-cols-2">
          <a
            href="https://github.com/connorkitchings/JamBandNerd"
            rel="noopener noreferrer"
            target="_blank"
            className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5 transition hover:border-primary"
          >
            <p className="font-headline text-base font-medium text-on-surface">GitHub</p>
            <p className="mt-1 text-xs text-on-surface-variant">
              Source code, docs, and contribution guidelines
            </p>
          </a>
          <Link
            href="/performance"
            className="rounded-xl border border-outline-variant/20 bg-surface-container-low p-5 transition hover:border-primary"
          >
            <p className="font-headline text-base font-medium text-on-surface">
              Performance Ledger
            </p>
            <p className="mt-1 text-xs text-on-surface-variant">
              Track historical accuracy across models and bands
            </p>
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}
