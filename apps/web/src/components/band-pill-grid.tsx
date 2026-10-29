import Link from "next/link";

export type BandPillLink = {
  href: string;
  label: string;
  active: boolean;
};

type Props = {
  links: BandPillLink[];
  className?: string;
  /** `row` keeps pills on one scrollable line on phones and wraps from `md` up. */
  layout?: "grid" | "row";
};

export function BandPillGrid({ links, className = "", layout = "grid" }: Props) {
  return (
    <div
      className={`gap-2 ${
        layout === "row"
          ? "flex overflow-x-auto pb-1 md:flex-wrap md:overflow-visible"
          : "grid auto-rows-fr"
      } ${className}`}
    >
      {links.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-current={item.active ? "page" : undefined}
          className={`touch-manipulation flex shrink-0 min-h-11 items-center justify-center rounded-full border px-4 py-2 text-center text-sm font-semibold transition ${
            item.active
              ? "border-accent bg-accent text-on-accent"
              : "border-line bg-surface text-on-surface hover:bg-surface-2"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </div>
  );
}
