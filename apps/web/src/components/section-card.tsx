import type { ReactNode } from "react";

type Props = {
  title: string;
  eyebrow?: string;
  headerAccessory?: ReactNode;
  children?: ReactNode;
  centered?: boolean;
};

export function SectionCard({
  title,
  eyebrow,
  headerAccessory,
  children,
  centered = false,
}: Props) {
  const align = centered ? "text-center" : "text-left";

  return (
    <section className="editorial-panel p-5 md:p-6">
      <div
        className={`relative flex gap-4 ${
          headerAccessory ? "flex-row items-start justify-between" : "flex-col"
        }`}
      >
        <div>
          {eyebrow ? (
            <p className={`text-xs font-bold uppercase tracking-[0.08em] text-on-surface-variant ${align}`}>
              {eyebrow}
            </p>
          ) : null}
          <h2 className={`mt-1 text-xl font-bold text-on-surface ${align}`}>{title}</h2>
        </div>
        {headerAccessory ? (
          <div className="ml-3 shrink-0 md:ml-4 md:min-w-44">{headerAccessory}</div>
        ) : null}
      </div>
      {children && <div className="relative mt-4">{children}</div>}
    </section>
  );
}
