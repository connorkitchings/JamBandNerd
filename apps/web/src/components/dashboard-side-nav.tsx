import Link from "next/link";

import { MobileControlSelects } from "@/components/mobile-control-selects";
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
  pathname?: string;
  bandLinks?: Array<{
    href: string;
    label: string;
    active: boolean;
  }>;
  hideSecondary?: boolean;
  secondaryLabel?: string;
  secondaryTone?: "primary" | "tertiary";
  secondaryLinks?: Array<{
    href: string;
    label: string;
    active: boolean;
  }>;
};

function buildHref(pathname: string, band: BandSlug, model: ModelSlug) {
  return `${pathname}?band=${band}&model=${model}`;
}

export function DashboardSideNav({
  band,
  model,
  bands,
  pathname = "/predictions",
  bandLinks,
  hideSecondary = false,
  secondaryLabel = "Model",
  secondaryTone = "tertiary",
  secondaryLinks,
}: Props) {
  const showModelButtons = !secondaryLinks;
  const renderedBandLinks =
    bandLinks ??
    bands.map((item) => ({
      href: buildHref(pathname, item.slug, model),
      label: item.displayName,
      active: item.slug === band,
    }));
  const renderedSecondaryLinks = showModelButtons
    ? ACTIVE_MODELS.map((item) => ({
        href: buildHref(pathname, band, item),
        label: MODEL_CONFIG[item].displayName,
        active: item === model,
      }))
    : (secondaryLinks ?? []);
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
    ...(!hideSecondary
      ? [
          {
            label: secondaryLabel,
            options: renderedSecondaryLinks,
            testId: "mobile-model-select",
          },
        ]
      : []),
  ];

  return (
    <div className="editorial-panel flex flex-col gap-4 p-4 md:p-5">
      <MobileControlSelects groups={mobileGroups} />

      <div
        className={`hidden items-stretch gap-4 md:grid ${
          hideSecondary
            ? "lg:grid-cols-1"
            : "lg:grid-cols-[minmax(0,1.6fr)_minmax(17rem,0.95fr)]"
        }`}
      >
        <div className="editorial-chip flex h-full flex-col rounded-[1.35rem] p-3 md:p-4">
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

        {!hideSecondary ? (
          <div className="editorial-chip flex h-full flex-col rounded-[1.35rem] p-3 md:p-4">
            <div className="mb-2 flex items-center justify-center text-center">
              <span
                className={`font-label text-[10px] font-semibold uppercase tracking-[0.24em] ${
                  secondaryTone === "primary"
                    ? "text-primary/85"
                    : "text-tertiary/85"
                }`}
              >
                {secondaryLabel}
              </span>
            </div>
            <div className="grid flex-1 content-center gap-2">
              <div className="grid grid-cols-2 gap-2">
                {renderedSecondaryLinks.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={item.active ? "page" : undefined}
                    className={`touch-manipulation flex min-h-11 items-center justify-center rounded-full border px-3 py-2 text-center font-headline text-[10px] font-bold uppercase tracking-[0.14rem] transition sm:text-[11px] ${
                      item.active
                        ? showModelButtons || secondaryTone === "primary"
                          ? "border-primary/25 bg-primary/12 text-primary"
                          : "border-tertiary/45 bg-tertiary/10 text-tertiary"
                        : showModelButtons || secondaryTone === "primary"
                          ? "border-outline-variant/40 bg-surface/75 text-on-surface-variant hover:border-primary/35 hover:text-on-surface"
                          : "border-outline-variant/40 bg-surface/75 text-on-surface-variant hover:border-tertiary/45 hover:text-tertiary"
                    }`}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
