import type { ReactNode } from "react";

type Props = {
  eyebrow?: string;
  title: ReactNode;
  description: string;
  descriptionClassName?: string;
  kicker?: string;
  meta?: ReactNode;
  aside?: ReactNode;
  centered?: boolean;
};

export function PageHero({
  eyebrow,
  title,
  description,
  descriptionClassName,
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
        <div className={centered ? "text-center" : "text-left"}>
          {kicker ? <span className="editorial-kicker">{kicker}</span> : null}
          {eyebrow ? (
            <p className="mt-3 text-xs font-bold uppercase tracking-[0.08em] text-accent-text">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="mt-2 max-w-4xl text-2xl font-bold text-on-surface md:text-4xl">
            {title}
          </h1>
          {meta ? (
            <div className="mt-3 text-sm font-bold text-accent-text md:text-base">{meta}</div>
          ) : null}
          <p
            className={`mt-3 max-w-3xl text-base text-on-surface-variant ${
              centered ? "mx-auto" : ""
            } ${descriptionClassName ?? ""}`}
          >
            {description}
          </p>
        </div>

        {aside ? <div className="relative">{aside}</div> : null}
      </div>
    </section>
  );
}
