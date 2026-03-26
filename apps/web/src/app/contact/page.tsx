import type { Metadata } from "next";

import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";

export const metadata: Metadata = {
  title: "Contact | JamBandNerd",
  description: "Get in touch with JamBandNerd about feedback, corrections, and collaboration.",
};

const CONTACT_EMAIL = "jambandnerd2026@gmail.com";

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <PageHero
        kicker="Direct line"
        eyebrow="Contact"
        title="Contact JamBandNerd"
        description="Use the email below for site feedback, data corrections, feature ideas, collaboration inquiries, or general questions about the project."
      />

      <SectionCard title="Email" eyebrow="Direct Contact">
        <div className="space-y-4 text-center">
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            aria-label={`Email ${CONTACT_EMAIL}`}
            className="inline-flex items-center rounded-full border border-primary/30 bg-primary/12 px-5 py-4 font-headline text-base font-medium text-primary transition hover:border-primary hover:bg-primary/16"
          >
            {CONTACT_EMAIL}
          </a>
          <p className="mx-auto max-w-2xl text-sm leading-6 text-on-surface-variant">
            Best for bug reports, incorrect setlist data, venue corrections, product feedback, and
            collaboration inquiries.
          </p>
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard title="Good Reasons To Reach Out" eyebrow="Examples">
          <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
            <p>Spotted a wrong setlist, venue, or show date.</p>
            <p>Have an idea for a feature, page, or prediction explanation.</p>
            <p>Want to suggest another band or data source.</p>
            <p>Attribution or Source Inquiries: Discussing how we credit your organization or link back to your archives.</p>
          </div>
        </SectionCard>

        <SectionCard title="What To Include" eyebrow="Helpful Context">
          <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
            <p>The band and page you were looking at.</p>
            <p>The exact show date, song, or venue if your note is data-related.</p>
            <p>A screenshot or short description of the issue if something looked broken.</p>
          </div>
        </SectionCard>
      </div>

      <p className="text-center text-xs text-on-surface-variant">
        By submitting data corrections, you grant JamBandNerd a non-exclusive license to use
        that factual information to improve our models.
      </p>
    </div>
  );
}
