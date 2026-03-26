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
        <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
          <p>
            Publicly available factual show information such as band names, show dates, venues,
            cities, regions, song titles, and song order.
          </p>
          <p>
            The site is built around facts and factual show metadata rather than expressive
            content, and does not treat that factual information as proprietary creative material.
          </p>
          <p>
            JamBandNerd also generates its own analytics, including prediction rankings, gap
            metrics, venue summaries, and accuracy calculations.
          </p>
          <p>
            Nonetheless, if a band or management group is uncomfortable with how data is being
            used or displayed here, please reach out and we will review it promptly.
          </p>
        </div>
      </SectionCard>

      <SectionCard title="Non-Substitutional Intent">
        <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
          <p>
            JamBandNerd is a companion tool for statistical analysis, not a replacement for
            community archives. We encourage users to visit original sources for full show
            histories.
          </p>
          <p>
            The site is designed to complement—not substitute for—the dedicated setlist archives
            maintained by fans and communities.
          </p>
        </div>
      </SectionCard>

      <SectionCard title="Expressive Content Disclaimer">
        <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
          <p>This site does not host lyrics, sheet music, audio/video files, or long-form editorial reviews.</p>
          <p>We focus exclusively on the mathematical analysis of factual setlist data.</p>
        </div>
      </SectionCard>

      <SectionCard title="Source Attribution And Model Credit">
        <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
          <p>
            JamBandNerd uses a dedicated online setlist source for each band, with some sources
            affiliated with the bands and some maintained independently. The site is intended to
            follow source terms of use while assembling factual show histories and setlist context.
          </p>
          <p>
            The Notebook method is based on the method developed by Phish.net.
          </p>
          <p>
            CK+ is a personally developed model created for this site.
          </p>
          <p>
            The product intent is to combine factual reference data with clearly labeled derived
            analytics rather than present all models as originating from the same source.
          </p>
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard title="What The Site Is Not Reproducing">
          <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
            <p>No lyrics, sheet music, or notation.</p>
            <p>No audio or video files.</p>
            <p>No long-form editorial writeups, articles, or expressive source material copied onto the site.</p>
            <p>No paywalled or authenticated source content is intended to be republished here.</p>
          </div>
        </SectionCard>

        <SectionCard title="Good-Faith Product Intent">
          <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
            <p>The site is meant to help users follow next-show predictions, compare historical outcomes, and explore venue or rotation patterns.</p>
            <p>The product is designed around factual reference data and internally generated analysis rather than expressive content.</p>
            <p>If any data appears inaccurate or creates a concern, we want to hear about it and review it promptly.</p>
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Notice and Takedown">
        <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
          <p>
            If you represent a band or data source and believe your content is used in a way that
            exceeds factual reference, please contact us at{" "}
            <a
              className="text-primary underline decoration-dotted"
              href={`mailto:${CONTACT_EMAIL}`}
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
          <p>
            We are committed to addressing concerns promptly and will review any takedown requests
            in good faith.
          </p>
        </div>
      </SectionCard>

      <SectionCard title="Questions Or Concerns">
        <div className="space-y-4 text-sm leading-6 text-on-surface-variant">
          <p>
            For corrections, attribution concerns, or general questions about how data is
            being displayed, contact{" "}
            <a
              className="text-primary underline decoration-dotted"
              href={`mailto:${CONTACT_EMAIL}`}
              aria-label={`Email ${CONTACT_EMAIL}`}
            >
              {CONTACT_EMAIL}
            </a>
            .
          </p>
          <p>
            This page is informational only and should not be treated as legal advice.
          </p>
          <p>
            You can also use the{" "}
            <Link className="text-primary underline decoration-dotted" href="/contact">
              contact page
            </Link>{" "}
            for general feedback or corrections.
          </p>
        </div>
      </SectionCard>
    </div>
  );
}
