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
    <div className="space-y-4">
      <div>
        <p className="mb-2 font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
          Band
        </p>
        <div className="flex flex-wrap gap-2">
          {bands.map((item) => {
            const active = item.slug === band;
            return (
              <Link
                key={item.slug}
                href={buildHref(pathname, item.slug, model, date)}
                className={`rounded-full border px-3 py-1.5 font-headline text-xs uppercase tracking-[0.14rem] transition ${
                  active
                    ? "border-primary-container bg-primary-container text-white"
                    : "border-outline-variant bg-surface-container-low text-on-surface-variant hover:border-primary hover:text-on-surface"
                }`}
              >
                {item.displayName}
              </Link>
            );
          })}
        </div>
      </div>
      {model ? (
        <div>
          <p className="mb-2 font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
            Model
          </p>
          <div className="flex flex-wrap gap-2">
            {ACTIVE_MODELS.map((item) => {
              const active = item === model;
              return (
                <Link
                  key={item}
                  href={buildHref(pathname, band, item, date)}
                  className={`rounded-full border px-3 py-1.5 font-headline text-xs uppercase tracking-[0.14rem] transition ${
                    active
                      ? "border-primary bg-primary text-[#002d6e]"
                      : "border-outline-variant bg-surface-container-low text-on-surface-variant hover:border-primary hover:text-on-surface"
                  }`}
                >
                  {MODEL_CONFIG[item].displayName}
                </Link>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
