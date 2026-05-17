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
      "It's the model's best guess at what a band will play at the next show. Songs near the top are the strongest reads, but it's still a guess — treat it like a conversation starter, not a setlist spoiler.",
  },
  {
    question: "What do avg. hits and coverage mean?",
    answer:
      "Avg. hits is how many of the model's picks actually got played. Coverage is how much of the real setlist the model managed to catch. Both are good to check before trusting the board too much.",
  },
  {
    question: "What drives the predictions?",
    answer:
      "Each band's model looks at setlist history, rotation patterns, song gaps, venue habits, and tour context. It turns all of that into a ranked list — but bands are unpredictable by nature, and that's part of the fun.",
  },
  {
    question: "Why does performance vary by band?",
    answer:
      "Some bands stick to tight rotations, some throw curveballs every night, and some have massive catalogs to pull from. We track each band on its own terms so you're not comparing apples to oranges.",
  },
  {
    question: "How often are predictions updated?",
    answer:
      "Daily. When new setlist information comes in, the boards and performance numbers get refreshed for all supported bands.",
  },
  {
    question: "What is Replay for?",
    answer:
      "Replay lets you look back at a finished show and see how the prediction board held up against what was actually played. Spoiler: the model doesn't always nail it, and that's fine.",
  },
  {
    question: "Where does the setlist data come from?",
    answer:
      "Each band has a dedicated setlist source online — some official, some run by fan communities. We use that factual show data carefully and keep our own predictions clearly separate.",
  },
];

const SITE_AREAS = [
  {
    step: "01",
    title: "Predictions",
    description:
      "See which songs the model likes for the next show. Take it with a grain of salt.",
  },
  {
    step: "02",
    title: "Performance",
    description:
      "Check avg. hits and coverage over recent shows to get a feel for how the model is doing.",
  },
  {
    step: "03",
    title: "Replay",
    description:
      "Look back at a finished show and compare the prediction board to the real setlist.",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <PageHero
        kicker="About"
        title="About JamBandNerd"
        description="JamBandNerd is a setlist prediction toy for jam band fans. It uses history and statistics to guess what might get played next — and then honestly tracks how those guesses turned out."
        descriptionClassName="md:max-w-4xl"
      />

      <SectionCard title="What The Site Does">
        <p className="mb-6 text-sm leading-6 text-on-surface-variant">
          Pick a band, see what the model thinks they&apos;ll play, and then check
          back after the show to see how it did. No guarantees — just educated
          guesses and honest scorekeeping.
        </p>
        <div className="editorial-chip rounded-[1.5rem] p-6">
          <p className="font-label text-[10px] uppercase tracking-[0.2em] text-primary">
            In plain terms
          </p>
          <ul className="mt-3 space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
            <li>The board is an attempt at a crystal ball. It will be correct sometimes and wrong a lot.</li>
            <li>Higher-ranked songs are stronger reads, but surprises happen every tour.</li>
            <li>After the show, check Performance or Replay to see what actually landed.</li>
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
