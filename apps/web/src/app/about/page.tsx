import { SectionCard } from "@/components/section-card";

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <SectionCard title="About JamBandNerd" eyebrow="Platform">
        <div className="space-y-4 text-sm leading-7 text-on-surface-variant">
          <p>
            JamBandNerd collects jam band setlists, transforms them in memory, and stores
            predictions plus historical accuracy in Supabase. GitHub Actions keeps the pipeline
            fresh, while this website becomes the long-term public delivery surface.
          </p>
          <p>
            The current website foundation already mirrors the core legacy read paths: latest
            predictions, predictions by date, per-show accuracy, and last-show setlists.
          </p>
          <p>
            The next phase is parity work: richer layout treatment, better comparison UX, explorer
            polish, and full replacement of the Streamlit product surface.
          </p>
        </div>
      </SectionCard>
    </div>
  );
}
