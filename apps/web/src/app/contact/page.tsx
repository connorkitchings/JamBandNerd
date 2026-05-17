import type { Metadata } from "next";

import { ContactActions } from "@/components/contact-actions";
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
        kicker="Contact"
        eyebrow="Contact"
        title="Contact JamBandNerd"
        description="Reach out if something looks wrong, a setlist detail needs correction, or you have feedback that would make the prediction and replay experience clearer."
      />

      <SectionCard title="Email" eyebrow="Direct Contact">
        <div className="space-y-4 text-center">
          <ContactActions email={CONTACT_EMAIL} />
          <p className="mx-auto max-w-2xl text-sm leading-6 text-on-surface-variant">
            Best for incorrect setlist data, venue corrections, prediction display
            issues, source questions, and suggestions for making the site easier to use.
          </p>
        </div>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard title="Good Reasons To Reach Out" eyebrow="Examples">
          <ul className="space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
            <li>Spotted a wrong setlist, venue, or show date.</li>
            <li>Have an idea that would make predictions or replay easier to understand.</li>
            <li>Want to suggest another band or data source.</li>
            <li>Need to discuss attribution, source credit, or archive links.</li>
          </ul>
        </SectionCard>

        <SectionCard title="What To Include" eyebrow="Helpful Context">
          <ul className="space-y-3 pl-5 text-sm leading-6 text-on-surface-variant marker:text-primary/75 list-disc">
            <li>The band and page you were looking at.</li>
            <li>The exact show date, song, or venue if your note is data-related.</li>
            <li>A screenshot or short description if something looked broken or confusing.</li>
          </ul>
        </SectionCard>
      </div>

      <p className="text-center text-xs text-on-surface-variant">
        By submitting data corrections, you grant JamBandNerd a non-exclusive license to use
        that factual information to improve our models.
      </p>
    </div>
  );
}
