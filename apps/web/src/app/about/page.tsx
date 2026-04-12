import type { Metadata } from "next";
import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";
import { MODEL_CONFIG } from "@/lib/config";

export const metadata: Metadata = {
  title: "About | JamBandNerd",
  description: "Learn how JamBandNerd collects setlists, transforms data, and generates predictions.",
};
const FAQ_ITEMS = [
  {
    question: "How do you measure accuracy?",
    answer:
      "Accuracy measures how much of the actual setlist was captured by the model's top predictions. For example, 30% accuracy at Top 10 means the model's top-10 group captured 30% of that night's actual songs. The site tracks that across multiple Top-X thresholds and shows the recent scoring history for each band and model.",
  },
  {
    question: "What drives the predictions?",
    answer:
      "Each model uses different signals:\n\nNotebook — An independent implementation of the weighted-recency algorithm popularized by Phish.net, provided as a benchmark for comparison. It emphasizes songs active in the recent rotation and uses current gap to separate likely candidates, while excluding songs played in the last 3 shows.\n\nDeal — A personally developed explainable logistic ranking model. It learns from true per-show candidate rows and shared rotation signals such as gap behavior, venue context, and recent activity patterns.",
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
    description:
      "Aggregates public, factual show metadata (dates, venues, song titles) from community archives.",
  },
  {
    step: "02",
    title: "Transform",
    description:
      "Normalizes raw facts into a proprietary feature set for statistical modeling.",
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
            <ul className="mt-3 space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
              <li>Weighted-recency benchmark inspired by the method popularized by Phish.net.</li>
              <li>Leans on active rotation trends and current gap to separate likely songs.</li>
              <li>Excludes songs played in the last 3 shows.</li>
            </ul>
            <p className="mt-4 border-t border-outline-variant/15 pt-4 font-label text-[10px] uppercase tracking-[0.16em] text-on-surface-variant">
              Credit: Based on the weighted-recency method popularized by Phish.net.
            </p>
          </div>
          <div className="editorial-chip rounded-[1.5rem] p-6">
            <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
              {MODEL_CONFIG.deal.displayName}
            </p>
            <ul className="mt-3 space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
              <li>Personally developed explainable ranking model built specifically for this site.</li>
              <li>Trains on true per-show candidate rows instead of relying on one fixed heuristic.</li>
              <li>Uses shared rotation, venue, and recency signals to produce calibrated song rankings.</li>
            </ul>
            <p className="mt-4 border-t border-outline-variant/15 pt-4 font-label text-[10px] uppercase tracking-[0.16em] text-on-surface-variant">
              Credit: Deal is an original personally developed model.
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
              <summary className="flex cursor-pointer list-none items-start justify-between gap-3 px-5 py-4 font-headline text-sm font-medium text-on-surface transition group-open:text-primary">
                <span className="pr-2">{item.question}</span>
                <svg
                  aria-hidden="true"
                  className="mt-0.5 size-4 shrink-0 text-on-surface-variant transition-transform group-open:rotate-180"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <path
                    d="M6 9L12 15L18 9"
                    stroke="currentColor"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.75"
                  />
                </svg>
              </summary>
              <p className="whitespace-pre-line px-5 pb-4 text-sm leading-6 text-on-surface-variant">
                {item.answer}
              </p>
            </details>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
