import type { Metadata } from "next";
import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";

export const metadata: Metadata = {
  title: "About | JamBandNerd",
  description:
    "Learn what JamBandNerd is and how to use its setlist predictions, performance pages, and replay tools.",
};

const FAQ_ITEMS = [
  {
    question: "What am I looking at on the Predictions page?",
    answer:
      "The Predictions page is the current ranked board for a selected band's next target show. Songs near the top are the model's strongest picks. The tiers help group the board into stronger and weaker signals, but the exact rank still matters.",
  },
  {
    question: "What do avg. hits and coverage mean?",
    answer:
      "Avg. hits asks: of the songs the model picked, how many were actually played? Coverage asks: of the songs actually played, how many did the model catch? Both matter, because a good setlist model should make useful picks and cover a meaningful share of the show.",
  },
  {
    question: "What drives the predictions?",
    answer:
      "The model looks at each band's setlist history, recent rotation, song gaps, tour context, venue patterns, and current show context. It turns those signals into a ranked list for the next target show.",
  },
  {
    question: "Why does performance vary by band?",
    answer:
      "Every band behaves differently. Some have tighter rotations, some have larger catalogs, and some change their setlists more aggressively. JamBandNerd tracks each band separately so you can judge the model in the right context.",
  },
  {
    question: "How often are predictions updated?",
    answer:
      "The site is designed around a daily refresh. When new setlist information is available, prediction boards and performance data are updated for the supported bands.",
  },
  {
    question: "What is Replay for?",
    answer:
      "Replay lets you look back at a completed show and compare the saved prediction board against the actual setlist. It is the easiest way to see what the model got right and where it missed.",
  },
  {
    question: "Where does the setlist data come from?",
    answer:
      "Each band has a dedicated setlist source online, with some sources affiliated with the bands and some maintained independently. We are careful to follow source terms of use, and the pipeline normalizes that factual show information into a shared show-centric format.",
  },
];

const SITE_AREAS = [
  {
    step: "01",
    title: "Predictions",
    description:
      "Open the current board for a band and see which songs the model likes most for the next target show.",
  },
  {
    step: "02",
    title: "Performance",
    description:
      "Check recent avg. hits and coverage to understand how useful the model has been over completed shows.",
  },
  {
    step: "03",
    title: "Replay",
    description:
      "Review saved prediction boards against the setlists that were actually played.",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHero
        kicker="About"
        title="About JamBandNerd"
        description="JamBandNerd helps frame what might happen at a band's next show. It uses setlist history and statistical modeling to rank likely songs, then tracks how those predictions hold up after the show."
        descriptionClassName="md:max-w-4xl"
      />

      <SectionCard title="What The Site Does">
        <p className="mb-6 text-sm leading-6 text-on-surface-variant">
          JamBandNerd is built for fans who want more than a gut feeling before
          the next show. Pick a band, scan the ranked prediction board, then use
          performance and replay pages to judge how well the model is actually
          doing.
        </p>
        <div className="editorial-chip rounded-[1.5rem] p-6">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
            In plain terms
          </p>
          <ul className="mt-3 space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
            <li>Use the prediction board as a starting point for what could be in play tonight.</li>
            <li>Higher-ranked songs are stronger model reads, not guarantees.</li>
            <li>After the show, check Performance or Replay to see what the model actually caught.</li>
          </ul>
        </div>
      </SectionCard>

      <SectionCard title="How To Use It">
        <div className="grid gap-4 md:grid-cols-3">
          {SITE_AREAS.map((item) => (
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
