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
    <div className="editorial-panel flex flex-col gap-4 p-4 md:p-5">
      <MobileControlSelects groups={mobileGroups} />

      <div className="hidden md:block">
        <div className="editorial-chip flex flex-col rounded-[1.35rem] p-3 md:p-4">
          <div className="mb-2 flex items-center justify-center text-center">
            <span className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-primary/85">
              Band
            </span>
          </div>
          <BandPillGrid links={renderedBandLinks} className="grid-cols-2 lg:grid-cols-3" />
        </div>
      </div>
    </div>
  );
}
