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
        kicker="Reference policy"
        eyebrow="Data use"
        title="Data Use"
        description="JamBandNerd is intended to present factual show information and its own derived analytics in a reference-style format. This page explains what the site uses and what it is designed not to reproduce."
      />

      <SectionCard title="What The Site Uses">
        <ul className="space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
          <li>Publicly available factual show information like band names, show dates, venues, cities, regions, song titles, and song order.</li>
          <li>Internally generated analytics such as prediction rankings, gap metrics, venue summaries, and accuracy calculations.</li>
          <li>Source-specific setlist histories assembled into a shared factual reference layer for analysis.</li>
        </ul>
      </SectionCard>

      <SectionCard title="What The Site Does Not Reproduce">
        <ul className="space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
          <li>No lyrics, sheet music, notation, or long-form editorial reviews.</li>
          <li>No audio or video files.</li>
          <li>No paywalled or authenticated source content.</li>
          <li>No attempt to replace dedicated community archives as the primary source of record.</li>
        </ul>
      </SectionCard>

      <SectionCard title="How The Product Is Positioned">
        <div className="space-y-4 text-sm leading-6 text-on-surface-variant">
          <p>
            JamBandNerd is a companion tool for statistical analysis, not a replacement for
            community archives. The product is meant to help users follow next-show predictions,
            compare historical outcomes, and explore venue or rotation patterns.
          </p>
          <p>
            JamBandNerd uses a dedicated online setlist source for each band, with some sources
            affiliated with the bands and some maintained independently. The site is intended to
            follow source terms of use while assembling factual show histories and clearly labeled
            derived analytics.
          </p>
          <p>
            The Notebook method is based on the method developed by Phish.net. Deal is a
            personally developed logistic ranking model created for this site.
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
