import Link from "next/link";

import {
  ACTIVE_MODELS,
  MODEL_CONFIG,
  type BandSlug,
  type ModelSlug,
} from "@/lib/config";
import type { BandEntry } from "@/lib/data";

type Props = {
  pathname: string;
  band: BandSlug;
  model?: ModelSlug;
  date?: string | null;
  bands: BandEntry[];
};

function buildHref(pathname: string, band: BandSlug, model?: ModelSlug, date?: string | null) {
  const params = new URLSearchParams();
  params.set("band", band);
  if (model) {
    params.set("model", model);
  }
  if (date) {
    params.set("date", date);
  }
  return `${pathname}?${params.toString()}`;
}

export function FilterLinks({ pathname, band, model, date, bands }: Props) {
  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-outline-variant/20 bg-surface-container-low p-4 xl:flex-row xl:items-center xl:justify-between">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:gap-8">
        
        {/* Band Selector */}
        <div className="flex flex-col gap-2 xl:flex-row xl:items-center">
          <div className="flex items-center xl:h-[72px]">
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
                  href={buildHref(pathname, item.slug, model, date)}
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

        {model ? (
          <>
            {/* Desktop Divider */}
            <div className="hidden h-6 w-px bg-outline-variant/30 xl:block" />

            {/* Model Selector */}
            <div className="flex flex-col gap-2 xl:flex-row xl:items-center">
              <div className="flex items-center xl:h-[72px]">
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
                      href={buildHref(pathname, band, item, date)}
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
          </>
        ) : null}
      </div>
    </div>
  );
}
