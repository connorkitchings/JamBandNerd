import { BandPillGrid } from "@/components/band-pill-grid";
import { MobileControlSelects } from "@/components/mobile-control-selects";
import { bandPath, type BandPage } from "@/lib/band-routes";
import type { BandSlug } from "@/lib/config";
import type { BandEntry } from "@/lib/data";

type Props = {
  band: BandSlug;
  bands: BandEntry[];
  /** Page the band picker keeps the visitor on when switching bands. */
  page: BandPage;
};

export function DashboardSideNav({ band, bands, page }: Props) {
  if (bands.length === 0) {
    return null;
  }

  const renderedBandLinks = bands.map((item) => ({
    href: bandPath(item.slug, page),
    label: item.displayName,
    active: item.slug === band,
  }));

  const mobileGroups = [
    {
      label: "Band",
      options: renderedBandLinks.map((item) => ({
        href: item.href,
        label: item.label,
        active: item.active,
      })),
      testId: "mobile-band-select",
    },
  ];

  return (
    <nav aria-label="Band" className="flex flex-col gap-4">
      <MobileControlSelects groups={mobileGroups} />

      <div className="hidden md:block">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant">
          Band
        </p>
        <BandPillGrid links={renderedBandLinks} className="grid-cols-2 lg:grid-cols-4" />
      </div>
    </nav>
  );
}
