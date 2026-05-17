import type { Metadata } from "next";
import Link from "next/link";

import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";

export const metadata: Metadata = {
  title: "Data Use | JamBandNerd",
  description:
    "How JamBandNerd uses public factual setlist information and its own derived analytics.",
};

const CONTACT_EMAIL = "jambandnerd2026@gmail.com";

export default function DataUsePage() {
  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <PageHero
        kicker="Data Use"
        eyebrow="Data use"
        title="Data Use"
        description="JamBandNerd uses public setlist facts to power prediction boards, performance summaries, and replay views. It is meant to add statistical context, not replace the archives and communities that document the shows."
      />

      <SectionCard title="What The Site Uses">
        <ul className="space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
          <li>Basic show facts such as band names, dates, venues, locations, song titles, and setlist order.</li>
          <li>Prediction and performance data created by JamBandNerd, including ranked boards, gaps, precision, recall, and replay matches.</li>
          <li>Setlist histories organized so each band&apos;s predictions can be scored after shows are completed.</li>
        </ul>
      </SectionCard>

      <SectionCard title="What The Site Does Not Reproduce">
        <ul className="space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
          <li>No lyrics, sheet music, notation, or long-form editorial reviews.</li>
          <li>No audio or video files.</li>
          <li>No paywalled or authenticated source content.</li>
          <li>No attempt to replace dedicated community archives or official sources of record.</li>
        </ul>
      </SectionCard>

      <SectionCard title="How The Product Is Positioned">
        <div className="space-y-4 text-sm leading-6 text-on-surface-variant">
          <p>
            JamBandNerd is a companion tool for setlist prediction and model performance.
            It helps users think about what could be in play at the next show, then gives
            them a way to check the model after the show is complete.
          </p>
          <p>
            Setlist sources vary by band. Some are official or affiliated, while others are
            maintained by independent communities. JamBandNerd uses those factual histories
            carefully and labels its own predictions and analytics separately.
          </p>
          <p>
            The prediction boards are not guarantees. They are statistical reads based on
            setlist history and current context, and the Performance and Replay pages show
            how those reads held up.
          </p>
        </div>
      </SectionCard>

      <SectionCard title="Questions, Notices, and Takedown">
        <div className="space-y-4 text-sm leading-6 text-on-surface-variant">
          <p>
            If you represent a band or data source and believe your content is used in a way that
            exceeds factual reference, contact{" "}
            <a
              className="text-primary underline decoration-dotted"
              href={`mailto:${CONTACT_EMAIL}`}
              aria-label={`Email ${CONTACT_EMAIL}`}
            >
              {CONTACT_EMAIL}
            </a>
            . We will review concerns in good faith.
          </p>
          <p>
            For corrections, attribution concerns, or general questions about how data is being
            displayed, you can also use the{" "}
            <Link className="text-primary underline decoration-dotted" href="/contact">
              contact page
            </Link>
            .
          </p>
          <p>This page is informational only and should not be treated as legal advice.</p>
        </div>
      </SectionCard>
    </div>
  );
}
