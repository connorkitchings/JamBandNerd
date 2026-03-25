import type { ReactNode } from "react";

type Props = {
  eyebrow: string;
  title: string;
  description: string;
  kicker?: string;
  meta?: string;
  aside?: ReactNode;
  centered?: boolean;
};

export function PageHero({
  eyebrow,
  title,
  description,
  kicker,
  meta,
  aside,
  centered = false,
}: Props) {
  return (
    <section className="editorial-hero px-5 py-6 md:px-10 md:py-10">
      <div
        className={`relative grid gap-5 md:gap-8 ${
          aside
            ? "lg:grid-cols-[minmax(0,1.35fr)_minmax(280px,0.65fr)] lg:items-center"
            : ""
        }`}
      >
        <div className={centered ? "text-center" : ""}>
          {kicker ? <span className="editorial-kicker">{kicker}</span> : null}
          {eyebrow ? (
            <p className="mt-3 font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="mt-3 max-w-4xl font-headline text-3xl font-bold uppercase tracking-[-0.05em] text-on-surface md:text-6xl">
            {title}
          </h1>
          {meta ? (
            <p className="mt-3 font-headline text-xs uppercase tracking-[0.14em] text-primary md:mt-4 md:text-base">
              {meta}
            </p>
          ) : null}
          <p
            className={`mt-4 max-w-3xl text-sm leading-6 text-on-surface-variant md:mt-5 md:text-[0.95rem] md:leading-7 ${
              centered ? "mx-auto" : ""
            }`}
          >
            {description}
          </p>
        </div>

        {aside ? <div className="relative">{aside}</div> : null}
      </div>
    </section>
  );
}
