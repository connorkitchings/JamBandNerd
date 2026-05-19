import { BandPillGrid } from "@/components/band-pill-grid";
import type { BandSlug } from "@/lib/config";
import { MobileControlSelects } from "@/components/mobile-control-selects";
import type { BandEntry } from "@/lib/data";

type Props = {
  pathname: string;
  band: BandSlug;
  date?: string | null;
  bands: BandEntry[];
};

function buildHref(pathname: string, band: BandSlug, date?: string | null) {
  const params = new URLSearchParams();
  params.set("band", band);
  if (date) {
    params.set("date", date);
  }
  return `${pathname}?${params.toString()}`;
}

export function FilterLinks({ pathname, band, date, bands }: Props) {
  const bandLinks = bands.map((item) => ({
    href: buildHref(pathname, item.slug, date),
    label: item.displayName,
    active: item.slug === band,
  }));
  const mobileGroups = [
    {
      label: "Band",
      options: bandLinks,
      testId: "mobile-band-select",
    },
  ];

  return (
    <div className="editorial-panel flex flex-col gap-3 p-3 md:gap-4 md:p-5">
      <MobileControlSelects groups={mobileGroups} />

      <div className="hidden flex-col gap-4 md:flex xl:flex-row xl:items-center xl:gap-8 w-full">
        <div className="flex flex-col gap-2 w-full xl:flex-row xl:items-center">
          <div className="flex items-center xl:h-[72px] xl:pr-4">
            <span className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
              Band
            </span>
          </div>
          <div className="overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <BandPillGrid links={bandLinks} className="md:flex md:flex-1 md:flex-wrap md:min-w-0" />
          </div>
        </div>
      </div>
    </div>
  );
}
