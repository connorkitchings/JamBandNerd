import type { Metadata } from "next";
import Link from "next/link";

import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";
import { MODEL_CONFIG } from "@/lib/config";
import { getBands } from "@/lib/data";

export const metadata: Metadata = {
  title: "About | JamBandNerd",
  description: "Learn how JamBandNerd collects setlists, transforms data, and generates predictions.",
};



const FAQ_ITEMS = [
  {
    question: "What is Top-10 Recall?",
    answer:
      "Recall measures how well the model's top predictions matched the actual setlist. For example, 30% recall at Top-10 means 3 out of every 10 predicted songs in the top-10 appeared in the show. We track this across the last 100 scored shows for each band and model.",
  },
  {
    question: "What drives the predictions?",
    answer:
      "Each model uses different signals:\n\nNotebook — Ranks songs by recent activity. Songs played most in the past year rise to the top, with songs that have larger gaps since their last performance ranked higher. Songs played in the last 3 shows are excluded.\n\nCK+ — Ranks songs by how overdue they are relative to their historical cadence. The score combines gap ratio (how much longer than average since last performance), gap z-score (how statistically unusual the current gap is), and reliability (songs with more consistent historical gaps and more plays get a boost). Songs played in the last 3 shows are excluded.",
  },
  {
    question: "Does accuracy vary by band?",
    answer:
      "Yes. Each band has a different catalog size, rotation pattern, and setlist variability. We track accuracy separately for each band. Check the Performance page to see how each model performs for a specific band.",
  },
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
      <PageHero
        kicker="Platform brief"
        eyebrow="About the platform"
        title="About JamBandNerd"
        description="JamBandNerd is a data platform that collects jam band setlists, transforms them into shared prediction features, and publishes a live website for next-show reads, historical replay, and model auditing."
        meta="Daily pipeline • multi-model prediction surface"
      />

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
                className="editorial-chip rounded-[1.5rem] p-6"
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
              href={`/predictions?band=${band.slug}`}
              className="editorial-chip rounded-[1.5rem] p-4 transition hover:border-primary hover:bg-surface-container"
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
              className="editorial-chip rounded-[1.5rem] p-5"
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
              className="group editorial-chip rounded-[1.5rem]"
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
          <Link
            href="/data-use"
            className="editorial-chip block rounded-[1.5rem] p-5 transition hover:border-primary"
          >
            <p className="font-headline text-base font-medium text-on-surface">
              Data Use
            </p>
            <p className="mt-1 text-xs text-on-surface-variant">
              Read how the site uses public factual information and derived analytics
            </p>
          </Link>
          <Link
            href="/contact"
            className="editorial-chip block rounded-[1.5rem] p-5 transition hover:border-primary"
          >
            <p className="font-headline text-base font-medium text-on-surface">
              Contact
            </p>
            <p className="mt-1 text-xs text-on-surface-variant">
              Reach out with feedback, corrections, or feature ideas
            </p>
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}
