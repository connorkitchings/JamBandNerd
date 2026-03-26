import type { Metadata } from "next";
import Link from "next/link";

import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";
import { MODEL_CONFIG } from "@/lib/config";

export const metadata: Metadata = {
  title: "About | JamBandNerd",
  description: "Learn how JamBandNerd collects setlists, transforms data, and generates predictions.",
};
const FAQ_ITEMS = [
  {
    question: "What is Top-10 Recall?",
    answer:
      "Recall measures how well the model's top predictions matched the actual setlist. For example, 30% recall at Top-10 means 3 out of every 10 predicted songs in the top-10 appeared in the show. We track this across the last 50 scored shows for each band and model in the current website views.",
  },
  {
    question: "What drives the predictions?",
    answer:
      "Each model uses different signals:\n\nNotebook — Based on the method developed by Phish.net. It emphasizes songs active in the recent rotation and uses current gap to separate likely candidates, while excluding songs played in the last 3 shows.\n\nCK+ — A personally developed model. It ranks songs by how overdue they are relative to their historical cadence, using gap ratio, gap z-score, and reliability signals. Songs played in the last 3 shows are excluded.",
  },
  {
    question: "Does accuracy vary by band?",
    answer:
      "Yes. Each band has a different catalog size, rotation pattern, and setlist variability. We track accuracy separately for each band. Check the Performance page to see how each model performs for a specific band.",
  },
  {
    question: "How often are predictions updated?",
    answer:
      "The pipeline runs daily at 3 PM ET. Each run collects the latest setlist data, re-generates predictions for every supported band and model, and publishes them to Supabase.",
  },
  {
    question: "What do the likelihood tiers mean?",
    answer:
      "Tiers (Expected, Hot, Likely, Possible) reflect relative ranking position rather than a precise probability. Expected songs have the strongest rotation signal, while Possible songs have lower recent activity but could still appear.",
  },
  {
    question: "Where does the setlist data come from?",
    answer:
      "Each band has a dedicated setlist source online, with some sources affiliated with the bands and some maintained independently. We are careful to follow source terms of use, and the pipeline normalizes that factual show information into a shared show-centric format.",
  },
  {
    question: "Can I use this data for my own projects?",
    answer:
      "The project is open-source under the MIT license. Reach out through the contact page if you have questions about reuse, attribution, or how the site is presenting data.",
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

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHero
        kicker="Platform brief"
        title="About JamBandNerd"
        description="JamBandNerd is a data platform that collects jam band setlists, transforms them into shared prediction features, and publishes a live website for next-show reads, historical replay, and model auditing."
        meta="Daily pipeline • multi-model prediction surface"
      />

      {/* Model Explainers */}
      <SectionCard title="How the Models Work">
        <p className="mb-6 text-sm leading-6 text-on-surface-variant">
          Two models generate independent predictions for every band. Each takes a distinct
          approach, which makes the Compare and Replay pages useful rather than redundant.
        </p>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="editorial-chip rounded-[1.5rem] p-6">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
              {MODEL_CONFIG.notebook.displayName}
            </p>
            <p className="mt-3 text-sm leading-6 text-on-surface-variant">
              A recency-first ranking model based on the Phish.net method. It focuses on songs
              active in the current rotation, then uses current gap to separate candidates while
              excluding songs played in the last 3 shows.
            </p>
            <p className="mt-4 border-t border-outline-variant/15 pt-4 font-label text-[10px] uppercase tracking-[0.16em] text-on-surface-variant">
              Credit: Notebook is based on the method developed by Phish.net.
            </p>
          </div>
          <div className="editorial-chip rounded-[1.5rem] p-6">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
              {MODEL_CONFIG.ckplus.displayName}
            </p>
            <p className="mt-3 text-sm leading-6 text-on-surface-variant">
              A personally developed cadence model that ranks songs by how overdue they are
              relative to their historical behavior, using gap ratio, gap z-score, and reliability
              signals.
            </p>
            <p className="mt-4 border-t border-outline-variant/15 pt-4 font-label text-[10px] uppercase tracking-[0.16em] text-on-surface-variant">
              Credit: CK+ is an original personally developed model.
            </p>
          </div>
        </div>
      </SectionCard>

      {/* Pipeline Overview */}
      <SectionCard title="The Pipeline">
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
      <SectionCard title="FAQ">
        <div className="space-y-4">
          {FAQ_ITEMS.map((item) => (
            <details
              key={item.question}
              className="group editorial-chip rounded-[1.5rem]"
            >
              <summary className="cursor-pointer select-none px-5 py-4 font-headline text-sm font-medium text-on-surface transition group-open:text-primary">
                {item.question}
              </summary>
              <p className="whitespace-pre-line px-5 pb-4 text-sm leading-6 text-on-surface-variant">
                {item.answer}
              </p>
            </details>
          ))}
        </div>
      </SectionCard>

      {/* Links */}
      <SectionCard title="Links">
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
              Reach out with feedback, corrections, or attribution questions
            </p>
          </Link>
        </div>
      </SectionCard>
    </div>
  );
}
