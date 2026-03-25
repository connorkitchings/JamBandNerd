import type { ReactNode } from "react";

type Props = {
  title: string;
  eyebrow?: string;
  children?: ReactNode;
  centered?: boolean;
};

export function SectionCard({ title, eyebrow, children, centered = false }: Props) {
  return (
    <section className="editorial-panel p-6 md:p-7">
      {eyebrow ? (
        <p
          className={`relative font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant ${
            centered ? "text-center" : ""
          }`}
        >
          {eyebrow}
        </p>
      ) : null}
      <h2
        className={`relative mt-2 font-headline text-[1.35rem] font-semibold uppercase tracking-[-0.03em] text-on-surface ${
          centered ? "text-center" : ""
        }`}
      >
        {title}
      </h2>
      {children && <div className="relative mt-5">{children}</div>}
    </section>
  );
}
