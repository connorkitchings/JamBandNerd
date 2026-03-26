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
  return (
    <section className="editorial-panel p-6 md:p-7">
      <div
        className={`relative flex flex-col gap-4 ${headerAccessory ? "md:flex-row md:items-start md:justify-between" : ""}`}
      >
        <div>
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
            className={`mt-2 font-headline text-[1.35rem] font-semibold uppercase tracking-[-0.03em] text-on-surface ${
              centered ? "text-center" : ""
            }`}
          >
            {title}
          </h2>
        </div>
        {headerAccessory ? <div className="md:ml-4 md:min-w-[11rem]">{headerAccessory}</div> : null}
      </div>
      {children && <div className="relative mt-5">{children}</div>}
    </section>
  );
}
