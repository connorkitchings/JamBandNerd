import Link from "next/link";

import {
  ACTIVE_MODELS,
  MODEL_CONFIG,
  type BandSlug,
  type ModelSlug,
} from "@/lib/config";
import type { BandEntry } from "@/lib/data";

type Props = {
  band: BandSlug;
  model: ModelSlug;
  bands: BandEntry[];
};

function buildHref(band: BandSlug, model: ModelSlug) {
  return `/predictions?band=${band}&model=${model}`;
}

export function DashboardSideNav({ band, model, bands }: Props) {
  return (
    <div className="mb-8 flex flex-col gap-5 rounded-2xl border border-outline-variant/20 bg-surface-container-low p-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:gap-8">
        
        {/* Band Selector */}
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <div className="flex items-center lg:h-[72px]">
            <span className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
              Band
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 2xl:flex 2xl:flex-wrap 2xl:items-center">
            {bands.map((item) => {
              const active = item.slug === band;
              return (
                <Link
                  key={item.slug}
                  href={buildHref(item.slug, model)}
                  className={`flex items-center justify-center rounded-full border px-3 py-1.5 text-center font-headline text-[11px] font-bold uppercase tracking-[0.12rem] transition ${
                    active
                      ? "border-primary-container bg-primary-container text-white"
                      : "border-outline-variant/50 bg-surface text-on-surface-variant hover:border-primary hover:text-on-surface"
                  }`}
                >
                  {item.displayName}
                </Link>
              );
            })}
          </div>
        </div>
        
        {/* Desktop Divider */}
        <div className="hidden h-6 w-px bg-outline-variant/30 lg:block" />

        {/* Model Selector */}
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          <div className="flex items-center lg:h-[72px]">
            <span className="font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
              Model
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2 2xl:flex 2xl:flex-wrap 2xl:items-center">
            {ACTIVE_MODELS.map((item) => {
              const active = item === model;
              return (
                <Link
                  key={item}
                  href={buildHref(band, item)}
                  className={`flex items-center justify-center rounded-full border px-3 py-1.5 text-center font-headline text-[11px] font-bold uppercase tracking-[0.12rem] transition ${
                    active
                      ? "border-primary bg-primary/15 text-primary"
                      : "border-outline-variant/50 bg-surface text-on-surface-variant hover:border-primary hover:text-on-surface"
                  }`}
                >
                  {MODEL_CONFIG[item].displayName}
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-1 lg:mt-0">
        <Link
          href={`/compare?band=${band}`}
          className="inline-flex w-full items-center justify-center rounded-lg border border-outline-variant/40 bg-surface px-4 py-2 text-center font-headline text-[11px] font-bold uppercase tracking-[0.18rem] text-on-surface transition hover:border-primary hover:bg-surface-container hover:text-primary lg:w-auto"
        >
          Compare Models
        </Link>
      </div>
    </div>
  );
}
