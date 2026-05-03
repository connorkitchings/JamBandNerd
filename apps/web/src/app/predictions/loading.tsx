import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";

export default function PredictionsLoading() {
  return (
    <>
      <PageHero title="Predictions" description="Loading..." />
      <SectionCard title="Predictions">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface-variant rounded w-1/3" />
          <div className="h-64 bg-surface-variant rounded" />
          <div className="h-64 bg-surface-variant rounded" />
        </div>
      </SectionCard>
    </>
  );
}
