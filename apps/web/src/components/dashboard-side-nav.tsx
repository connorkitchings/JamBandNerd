import Link from "next/link";

import {
  ACTIVE_BANDS,
  ACTIVE_MODELS,
  BAND_CONFIG,
  MODEL_CONFIG,
  type BandSlug,
  type ModelSlug,
} from "@/lib/config";

type Props = {
  band: BandSlug;
  model: ModelSlug;
};

function buildHref(band: BandSlug, model: ModelSlug) {
  return `/?band=${band}&model=${model}`;
}

export function DashboardSideNav({ band, model }: Props) {
  return (
    <>
      {/* Mobile filter strip */}
      <div className="mb-6 space-y-3 lg:hidden">
        <div>
          <p className="mb-2 font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
            Band
          </p>
          <div className="flex flex-wrap gap-2">
            {ACTIVE_BANDS.map((item) => {
              const active = item === band;
              return (
                <Link
                  key={item}
                  href={buildHref(item, model)}
                  className={`rounded-full border px-3 py-1.5 font-headline text-xs uppercase tracking-[0.14rem] transition ${
                    active
                      ? "border-primary-container bg-primary-container text-white"
                      : "border-outline-variant bg-surface-container-low text-on-surface-variant hover:border-primary hover:text-on-surface"
                  }`}
                >
                  {BAND_CONFIG[item].displayName}
                </Link>
              );
            })}
          </div>
        </div>
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
                  href={buildHref(band, item)}
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
      </div>

      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 hidden h-screen w-64 flex-col border-r border-white/15 bg-surface-container py-8 pt-24 lg:flex">
        <div className="px-6">
          <h3 className="font-headline text-lg font-bold text-on-surface">Global Filters</h3>
          <p className="font-label text-[10px] font-medium uppercase tracking-[0.24rem] text-on-surface/50">
            Archivist Parameters
          </p>
        </div>

        <div className="mt-6 space-y-8 px-3">
          <div className="space-y-1">
            <p className="px-3 font-label text-[10px] uppercase tracking-[0.2rem] text-on-surface/40">
              Bands
            </p>
            {ACTIVE_BANDS.map((item) => {
              const active = item === band;
              return (
                <Link
                  key={item}
                  href={buildHref(item, model)}
                  className={`flex items-center gap-3 px-3 py-3 font-headline text-xs font-medium uppercase transition-all ${
                    active
                      ? "border-l-4 border-primary-container bg-surface-container-high text-primary"
                      : "text-on-surface/50 hover:bg-surface-container-high/60 hover:text-on-surface"
                  }`}
                >
                  <span className="text-sm">{active ? "◉" : "○"}</span>
                  {BAND_CONFIG[item].displayName}
                </Link>
              );
            })}
          </div>

          <div className="space-y-1">
            <p className="px-3 font-label text-[10px] uppercase tracking-[0.2rem] text-on-surface/40">
              Models
            </p>
            {ACTIVE_MODELS.map((item) => {
              const active = item === model;
              return (
                <Link
                  key={item}
                  href={buildHref(band, item)}
                  className={`flex items-center gap-3 px-3 py-3 font-headline text-xs font-medium uppercase transition-all ${
                    active
                      ? "border-l-4 border-primary-container bg-surface-container-high text-primary"
                      : "text-on-surface/50 hover:bg-surface-container-high/60 hover:text-on-surface"
                  }`}
                >
                  <span className="text-sm">{active ? "◆" : "◇"}</span>
                  {MODEL_CONFIG[item].displayName}
                </Link>
              );
            })}
          </div>
        </div>

        <div className="mt-auto px-6">
          <Link
            href={`/compare?band=${band}`}
            className="block w-full rounded-lg bg-primary-container px-4 py-3 text-center font-headline text-xs uppercase tracking-[0.18rem] text-white transition hover:opacity-90"
          >
            Compare Models
          </Link>
        </div>
      </aside>
    </>
  );
}
