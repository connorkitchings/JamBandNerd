import Link from "next/link";

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
  const mobileGroups = [
    {
      label: "Band",
      options: bands.map((item) => ({
        href: buildHref(pathname, item.slug, date),
        label: item.displayName,
        active: item.slug === band,
      })),
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
            <div className="gap-2 md:flex md:flex-1 md:flex-wrap md:min-w-0">
              {bands.map((item) => {
                const active = item.slug === band;
                return (
                  <Link
                    key={item.slug}
                    href={buildHref(pathname, item.slug, date)}
                    aria-current={active ? "page" : undefined}
                    className={`touch-manipulation flex items-center justify-center rounded-full border px-4 py-2.5 text-center font-headline text-[11px] font-bold uppercase tracking-[0.14rem] transition whitespace-nowrap ${
                      active
                        ? "border-primary/25 bg-primary/12 text-primary"
                        : "border-outline-variant/40 bg-surface/75 text-on-surface-variant hover:border-primary/35 hover:text-on-surface"
                    }`}
                  >
                    {item.displayName}
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
