import { PageHero } from "@/components/page-hero";
import { SectionCard } from "@/components/section-card";

export default function CompareLoading() {
  return (
    <>
      <PageHero title="Compare" description="Loading..." />
      <SectionCard title="Compare">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-surface-variant rounded w-1/3" />
          <div className="h-96 bg-surface-variant rounded" />
        </div>
      </SectionCard>
    </>
  );
}
