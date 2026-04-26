import Link from "next/link";

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
          <div className="grid auto-rows-fr grid-cols-2 gap-2 lg:grid-cols-3">
            {renderedBandLinks.map((item) => {
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={item.active ? "page" : undefined}
                  className={`touch-manipulation flex min-h-11 items-center justify-center rounded-full border px-3 py-2 text-center font-headline text-[10px] font-bold uppercase tracking-[0.14rem] transition sm:text-[11px] ${
                    item.active
                      ? "border-primary/25 bg-primary/12 text-primary"
                      : "border-outline-variant/40 bg-surface/75 text-on-surface-variant hover:border-primary/35 hover:text-on-surface"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
