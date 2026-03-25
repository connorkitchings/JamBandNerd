import type { Metadata } from "next";

import { SectionCard } from "@/components/section-card";

export const metadata: Metadata = {
  title: "Contact | JamBandNerd",
  description: "Get in touch with JamBandNerd about feedback, corrections, and collaboration.",
};

const CONTACT_EMAIL = "jambandnerd2026@gmail.com";

export default function ContactPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <section className="relative overflow-hidden rounded-xl border border-outline-variant/30 bg-surface-container p-8 md:p-12">
        <div className="absolute inset-y-0 right-0 hidden w-1/3 bg-gradient-to-l from-primary-container/15 to-transparent lg:block" />
        <div className="relative">
          <p className="font-label text-[10px] uppercase tracking-[0.24em] text-on-surface-variant">
            Contact
          </p>
          <h1 className="mt-3 font-headline text-4xl font-semibold uppercase tracking-[-0.04em] text-on-surface md:text-5xl">
            Contact JamBandNerd
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-on-surface-variant">
            Use the email below for site feedback, data corrections, feature ideas, or general
            questions about the project.
          </p>
        </div>
      </section>

      <SectionCard title="Email" eyebrow="Direct Contact">
        <a
          href={`mailto:${CONTACT_EMAIL}`}
          aria-label={`Email ${CONTACT_EMAIL}`}
          className="inline-flex items-center rounded-xl border border-primary/30 bg-primary-container/10 px-5 py-4 font-headline text-base font-medium text-primary transition hover:border-primary hover:bg-primary-container/20"
        >
          {CONTACT_EMAIL}
        </a>
        <p className="mt-4 text-sm leading-6 text-on-surface-variant">
          Best for bug reports, incorrect setlist data, venue corrections, product feedback, and
          collaboration inquiries.
        </p>
      </SectionCard>

      <div className="grid gap-4 md:grid-cols-2">
        <SectionCard title="Good Reasons To Reach Out" eyebrow="Examples">
          <div className="space-y-3 text-sm leading-6 text-on-surface-variant">
            <p>Spotted a wrong setlist, venue, or show date.</p>
            <p>Have an idea for a feature, page, or prediction explanation.</p>
            <p>Want to suggest another band or data source.</p>
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
    </div>
  );
}
