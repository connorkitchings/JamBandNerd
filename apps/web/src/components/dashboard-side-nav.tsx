import { BandPillGrid } from "@/components/band-pill-grid";
import { MobileControlSelects } from "@/components/mobile-control-selects";
import type { BandSlug } from "@/lib/config";
import type { BandEntry } from "@/lib/data";

type Props = {
  band: BandSlug;
  bands: BandEntry[];
  pathname?: string;
  bandLinks?: Array<{
    href: string;
    label: string;
    active: boolean;
  }>;
};

function buildHref(pathname: string, band: BandSlug) {
  return `${pathname}?band=${band}`;
}

export function DashboardSideNav({
  band,
  bands,
  pathname = "/predictions",
  bandLinks,
}: Props) {
  const renderedBandLinks =
    bandLinks ??
    bands.map((item) => ({
      href: buildHref(pathname, item.slug),
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
