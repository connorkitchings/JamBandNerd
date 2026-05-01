import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";

export default function LastShowLoading() {
  return (
    <>
      <PageHero title="Last Show" description="Loading..." />
      <SectionCard title="Last Show">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface-variant rounded w-1/3" />
          <div className="h-96 bg-surface-variant rounded" />
        </div>
      </SectionCard>
    </>
  );
}
