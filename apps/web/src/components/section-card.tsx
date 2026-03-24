import type { ReactNode } from "react";

type Props = {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  centered?: boolean;
};

export function SectionCard({ title, eyebrow, children, centered = false }: Props) {
  return (
    <section className="rounded-xl border border-outline-variant/30 bg-surface-container p-6 shadow-[0_0_0_1px_rgba(255,255,255,0.02)]">
      {eyebrow ? (
        <p
          className={`font-label text-[10px] font-semibold uppercase tracking-[0.24em] text-on-surface-variant ${
            centered ? "text-center" : ""
          }`}
        >
          {eyebrow}
        </p>
      ) : null}
      <h2
        className={`mt-2 font-headline text-xl font-semibold text-on-surface ${
          centered ? "text-center" : ""
        }`}
      >
        {title}
      </h2>
      <div className="mt-5">{children}</div>
    </section>
  );
}
